"""Tests de l'ingestion DPE avec une fausse API (sans réseau)."""

import duckdb
import pytest
import requests

import config
from ingestion import ingest_dpe


def dpe(num, modif, etiquette="D"):
    return {"numero_dpe": num, "date_derniere_modification_dpe": modif, "etiquette_dpe": etiquette,
            "code_departement_ban": "69", "surface_habitable_logement": 52.5, "colonne_inutile": "x"}


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


class FakeSession:
    """Simule l'API : 2 pages reliées par un lien « next », et enregistre les requêtes."""

    def __init__(self, pages, fail_first=0):
        self.pages, self.calls, self.fail_first = pages, [], fail_first

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        if self.fail_first:
            self.fail_first -= 1
            return FakeResponse({}, 429)
        if url.endswith("/page2"):
            return FakeResponse({"total": 3, "results": self.pages[1]})
        return FakeResponse({"total": 3, "results": self.pages[0], "next": "https://api/page2"})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(ingest_dpe.time, "sleep", lambda s: None)


def read(dep_dir):
    return duckdb.connect().execute(f"SELECT * FROM '{dep_dir.as_posix()}/part-*.parquet' ORDER BY numero_dpe").fetchall()


def test_pagination_et_colonnes(tmp_path):
    s = FakeSession([[dpe("A", "2026-01-01"), dpe("B", "2026-01-02")], [dpe("C", "2026-01-03")]])
    n = ingest_dpe.ingest_departement(s, "ds", "69", tmp_path)
    assert n == 3
    con = duckdb.connect()
    cols = [d[0] for d in con.execute(f"SELECT * FROM '{(tmp_path / 'dep=69').as_posix()}/part-*.parquet'").description]
    assert [c for c in cols if c != "dep"] == config.DPE_COLUMNS + ["_ingere_le"]  # « dep » vient du nom du dossier
    assert s.calls[0][1]["qs"] == 'code_departement_ban:"69"'    # premier passage : pas de filtre de date
    assert not list((tmp_path / "dep=69").glob(".tmp-*"))        # aucun fichier temporaire laissé


def test_incremental_ne_demande_que_les_nouveautes(tmp_path):
    ingest_dpe.ingest_departement(FakeSession([[dpe("A", "2026-01-01")], [dpe("B", "2026-02-15")]]), "ds", "69", tmp_path)
    s2 = FakeSession([[dpe("B", "2026-03-01", "C")], []])
    ingest_dpe.ingest_departement(s2, "ds", "69", tmp_path)
    assert "date_derniere_modification_dpe:>=2026-02-15" in s2.calls[0][1]["qs"]
    assert len(list((tmp_path / "dep=69").glob("part-*.parquet"))) >= 1


def test_nouvelle_tentative_si_limite_de_debit(tmp_path):
    s = FakeSession([[dpe("A", "2026-01-01")], []], fail_first=2)
    assert ingest_dpe.ingest_departement(s, "ds", "69", tmp_path) == 1


def test_echec_reseau_ne_laisse_aucun_fichier_partiel(tmp_path):
    class Broken(FakeSession):
        def get(self, url, params=None, timeout=None):
            if url.endswith("/page2"):
                raise requests.ConnectionError("coupure")
            return super().get(url, params, timeout)
    with pytest.raises(requests.ConnectionError):
        ingest_dpe.ingest_departement(Broken([[dpe("A", "2026-01-01")], []]), "ds", "69", tmp_path)
    assert not list((tmp_path / "dep=69").glob("*"))


def test_rechargement_complet_remplace_l_ancien(tmp_path):
    ingest_dpe.ingest_departement(FakeSession([[dpe("A", "2026-01-01")], []]), "ds", "69", tmp_path)
    ingest_dpe.ingest_departement(FakeSession([[dpe("X", "2026-05-01")], []]), "ds", "69", tmp_path, full=True)
    assert [r[0] for r in read(tmp_path / "dep=69")] == ["X"]
