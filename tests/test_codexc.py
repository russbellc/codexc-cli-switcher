"""Suite unitaria hermética para codexc (Windows 10/11 y Linux)."""

import argparse
import importlib.machinery
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from lib.platform import linux as platform_linux
from lib.platform import win32 as platform_win32


def load_codexc_module():
    """Carga bin/codexc como módulo Python aunque no tenga extensión .py."""
    codexc_path = os.path.join(REPO_ROOT, "bin", "codexc")
    loader = importlib.machinery.SourceFileLoader("codexc_cli", codexc_path)
    spec = importlib.util.spec_from_loader("codexc_cli", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


codexc = load_codexc_module()


class CodexcTestCase(unittest.TestCase):
    """Base hermética con directorios temporales aislados."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.real_home = os.path.join(self.root, "home")
        self.codexc_dir = os.path.join(self.real_home, ".codexc")
        self.cache_dir = os.path.join(self.codexc_dir, "cache")
        self.homes_dir = os.path.join(self.real_home, ".codexc_homes")
        self.system_codex_dir = os.path.join(self.real_home, ".codex")
        self.local_bin_dir = os.path.join(self.root, "local_bin")
        self.active_file = os.path.join(self.codexc_dir, "active")
        self.default_file = os.path.join(self.codexc_dir, "default")

        os.makedirs(self.real_home, exist_ok=True)
        os.makedirs(self.system_codex_dir, exist_ok=True)
        os.makedirs(self.local_bin_dir, exist_ok=True)

        self.fake_real_bin = os.path.join(
            self.root, "real_codex", "codex.cmd" if os.name == "nt" else "codex"
        )
        os.makedirs(os.path.dirname(self.fake_real_bin), exist_ok=True)
        with open(self.fake_real_bin, "w", encoding="utf-8") as f:
            if os.name == "nt":
                f.write("@echo off\r\necho CODEX_HOME=%CODEX_HOME% ARGS=%*\r\n")
            else:
                f.write("#!/usr/bin/env bash\necho \"CODEX_HOME=$CODEX_HOME ARGS=$*\"\n")
                os.chmod(self.fake_real_bin, 0o755)

        self.patchers = [
            mock.patch.object(codexc, "REAL_HOME", self.real_home),
            mock.patch.object(codexc, "CODEXC_DIR", self.codexc_dir),
            mock.patch.object(codexc, "CACHE_DIR", self.cache_dir),
            mock.patch.object(codexc, "HOMES_DIR", self.homes_dir),
            mock.patch.object(codexc, "SYSTEM_CODEX_DIR", self.system_codex_dir),
            mock.patch.object(codexc, "LOCAL_BIN_DIR", self.local_bin_dir),
            mock.patch.object(codexc, "ACTIVE_FILE", self.active_file),
            mock.patch.object(codexc, "DEFAULT_FILE", self.default_file),
            mock.patch.object(codexc, "get_real_codex_bin", return_value=self.fake_real_bin),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        self.tmp.cleanup()

    def _create_profile(self, alias: str, access_token: str = "tok-123", account_id: str = "acc-1"):
        prof_dir = os.path.join(self.homes_dir, alias)
        os.makedirs(prof_dir, exist_ok=True)
        auth_path = os.path.join(prof_dir, "auth.json")
        with open(auth_path, "w", encoding="utf-8") as f:
            json.dump(
                {"tokens": {"access_token": access_token, "account_id": account_id}},
                f,
            )
        return prof_dir


class TestValidateAliasAndList(CodexcTestCase):
    def test_validate_alias_accepts_valid(self):
        self.assertEqual(codexc.validate_alias("  codex01  "), "codex01")
        self.assertEqual(codexc.validate_alias("codex_work-2"), "codex_work-2")

    def test_validate_alias_rejects_invalid_and_reserved(self):
        for bad in ("", "   ", "../evil", "a/b", "a" * 33, "codex", "codexc", "all", "null"):
            with self.assertRaises(ValueError, msg=f"Debió rechazar: {bad!r}"):
                codexc.validate_alias(bad)

    def test_list_aliases_filters_and_sorts(self):
        self._create_profile("codex02")
        self._create_profile("codex01")
        os.makedirs(os.path.join(self.homes_dir, "codex_no_auth"), exist_ok=True)
        os.makedirs(os.path.join(self.homes_dir, "other_dir"), exist_ok=True)
        with open(os.path.join(self.homes_dir, "other_dir", "auth.json"), "w", encoding="utf-8") as f:
            f.write("{}")
        self.assertEqual(codexc.list_aliases(), ["codex01", "codex02"])


class TestAutoMigration(CodexcTestCase):
    def test_ensure_auto_migration_creates_codex01_and_links_skills(self):
        with open(os.path.join(self.system_codex_dir, "auth.json"), "w", encoding="utf-8") as f:
            json.dump({"tokens": {"access_token": "mig-tok"}}, f)
        with open(os.path.join(self.system_codex_dir, "config.toml"), "w", encoding="utf-8") as f:
            f.write("model = 'gpt-5'\n")
        skills_src = os.path.join(self.system_codex_dir, "skills")
        os.makedirs(skills_src, exist_ok=True)
        with open(os.path.join(skills_src, "demo.txt"), "w", encoding="utf-8") as f:
            f.write("ok")

        codexc.ensure_auto_migration()

        self.assertEqual(codexc.list_aliases(), ["codex01"])
        prof_dir = os.path.join(self.homes_dir, "codex01")
        self.assertTrue(os.path.isfile(os.path.join(prof_dir, "auth.json")))
        self.assertTrue(os.path.isfile(os.path.join(prof_dir, "config.toml")))
        skills_dst = os.path.join(prof_dir, "skills")
        self.assertTrue(os.path.isdir(skills_dst))
        self.assertTrue(os.path.isfile(os.path.join(skills_dst, "demo.txt")))
        self.assertEqual(codexc.get_active_alias(), "codex01")
        self.assertEqual(codexc.get_default_alias(), "codex01")


class TestNativeTokenRefresh(CodexcTestCase):
    def test_attempt_native_token_refresh_success_with_pipe(self):
        self._create_profile("codex01")
        r_fd, w_fd = os.pipe()
        r_stream = os.fdopen(r_fd, "rb", buffering=0)
        w_stream = os.fdopen(w_fd, "wb", buffering=0)

        fake_proc = mock.MagicMock()
        fake_proc.stdin = io.BytesIO()
        fake_proc.stdout = r_stream
        fake_proc.poll.return_value = 0

        def writer():
            w_stream.write(b'{"id": 1, "result": {"serverInfo": {}}}\n')
            w_stream.write(b'{"id": 2, "result": {"account": {"email": "dev1@gmail.com"}}}\n')
            w_stream.flush()
            w_stream.close()

        import threading
        t = threading.Thread(target=writer, daemon=True)
        t.start()

        try:
            with mock.patch.object(codexc.subprocess, "Popen", return_value=fake_proc):
                ok = codexc.attempt_native_token_refresh("codex01")
        finally:
            t.join(timeout=1.0)
            try:
                r_stream.close()
            except Exception:
                pass

        self.assertTrue(ok)
        fake_proc.terminate.assert_called()

    def test_attempt_native_token_refresh_returns_false_without_account(self):
        self._create_profile("codex01")
        fake_proc = mock.MagicMock()
        fake_proc.stdin = io.BytesIO()
        fake_proc.stdout = io.BytesIO(b'{"id": 2, "result": {}}\n')
        fake_proc.poll.return_value = 0

        with mock.patch.object(codexc.subprocess, "Popen", return_value=fake_proc):
            ok = codexc.attempt_native_token_refresh("codex01")

        self.assertFalse(ok)
        fake_proc.terminate.assert_called()


class TestSyncLaunchers(CodexcTestCase):
    def test_sync_launchers_windows_cmd_generation_and_execution(self):
        self._create_profile("codex01")
        with mock.patch.object(codexc, "IS_WINDOWS", True), mock.patch.object(
            codexc, "get_launcher_path", side_effect=platform_win32.get_launcher_path
        ), mock.patch.object(
            codexc, "set_executable_permissions", side_effect=platform_win32.set_executable_permissions
        ):
            codexc.sync_launchers()

        launcher = os.path.join(self.local_bin_dir, "codex01.cmd")
        wrapper = os.path.join(self.local_bin_dir, "codex.cmd")
        codexc_cmd = os.path.join(self.local_bin_dir, "codexc.cmd")

        self.assertTrue(os.path.isfile(launcher))
        self.assertTrue(os.path.isfile(wrapper))
        self.assertTrue(os.path.isfile(codexc_cmd))

        with open(launcher, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("@echo off", content)
        self.assertIn("KNOWN_SUBS=", content)
        self.assertIn("--yolo", content)
        self.assertIn("--no-yolo", content)

        if os.name == "nt":
            res_default = subprocess.run(
                ["cmd", "/c", launcher, "fix bug"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("--yolo", res_default.stdout)
            self.assertIn("codex01", res_default.stdout)

            res_no_yolo = subprocess.run(
                ["cmd", "/c", launcher, "--no-yolo", "fix bug"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertNotIn("--yolo", res_no_yolo.stdout)
            self.assertNotIn("--no-yolo", res_no_yolo.stdout)

            res_sub = subprocess.run(
                ["cmd", "/c", launcher, "exec", "status"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertNotIn("--yolo", res_sub.stdout)
            self.assertIn("exec", res_sub.stdout)

    def test_sync_launchers_linux_bash_generation(self):
        self._create_profile("codex01")
        with mock.patch.object(codexc, "IS_WINDOWS", False), mock.patch.object(
            codexc, "get_launcher_path", side_effect=platform_linux.get_launcher_path
        ), mock.patch.object(
            codexc, "set_executable_permissions", lambda p: None
        ), mock.patch.object(os, "symlink", lambda s, d: None):
            codexc.sync_launchers()

        launcher = os.path.join(self.local_bin_dir, "codex01")
        wrapper = os.path.join(self.local_bin_dir, "codex")
        self.assertTrue(os.path.isfile(launcher))
        self.assertTrue(os.path.isfile(wrapper))
        with open(launcher, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue(content.startswith("#!/usr/bin/env bash"))
        self.assertIn("KNOWN_SUBS=", content)
        self.assertIn("--no-yolo", content)


class TestFetchUsageAndRotation(CodexcTestCase):
    def test_fetch_codex_usage_uses_cache_within_ttl(self):
        self._create_profile("codex01")
        os.makedirs(self.cache_dir, exist_ok=True)
        now = time.time()
        cache_path = os.path.join(self.cache_dir, "codex01.json")
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "alias": "codex01",
                    "email": "dev1@gmail.com",
                    "primary_window": {"remaining_fraction": 0.8, "reset_at": now + 3600},
                    "secondary_window": {"remaining_fraction": 0.9, "reset_at": now + 7200},
                    "cached_at": now,
                },
                f,
            )

        with mock.patch.object(codexc.urllib.request, "urlopen") as mocked_open:
            usage = codexc.fetch_codex_usage("codex01", force_refresh=False)

        mocked_open.assert_not_called()
        self.assertEqual(usage["email"], "dev1@gmail.com")
        self.assertGreater(usage["primary_window"]["reset_after_seconds"], 0)

    def test_fetch_codex_usage_401_triggers_refresh_and_retries(self):
        self._create_profile("codex01")
        err_401 = urllib.error.HTTPError(
            url="https://chatgpt.com/backend-api/codex/usage",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )
        ok_payload = json.dumps(
            {
                "email": "dev1@gmail.com",
                "user_id": "u-1",
                "account_id": "acc-1",
                "plan_type": "plus",
                "rate_limit": {
                    "allowed": True,
                    "limit_reached": False,
                    "primary_window": {"used_percent": 20, "reset_after_seconds": 1800},
                    "secondary_window": {"used_percent": 10, "reset_after_seconds": 86400},
                },
            }
        ).encode("utf-8")

        fake_resp = mock.MagicMock()
        fake_resp.read.return_value = ok_payload
        fake_resp.__enter__.return_value = fake_resp

        with mock.patch.object(
            codexc.urllib.request, "urlopen", side_effect=[err_401, fake_resp]
        ), mock.patch.object(codexc, "attempt_native_token_refresh", return_value=True) as mock_ref:
            usage = codexc.fetch_codex_usage("codex01", force_refresh=True)

        mock_ref.assert_called_once_with("codex01")
        self.assertEqual(usage["email"], "dev1@gmail.com")
        self.assertAlmostEqual(usage["primary_window"]["remaining_fraction"], 0.8)

    def test_cmd_auto_selects_highest_available_quota(self):
        self._create_profile("codex01", account_id="acc-1")
        self._create_profile("codex02", account_id="acc-2")

        usage_map = {
            "codex01": {
                "alias": "codex01",
                "email": "dev1@gmail.com",
                "allowed": True,
                "limit_reached": False,
                "primary_window": {"remaining_fraction": 0.25},
                "secondary_window": {"remaining_fraction": 0.90},
            },
            "codex02": {
                "alias": "codex02",
                "email": "dev2@gmail.com",
                "allowed": True,
                "limit_reached": False,
                "primary_window": {"remaining_fraction": 0.85},
                "secondary_window": {"remaining_fraction": 0.70},
            },
        }

        with mock.patch.object(
            codexc, "fetch_codex_usage", side_effect=lambda alias, force_refresh=False: usage_map[alias]
        ):
            codexc.cmd_auto(argparse.Namespace())

        self.assertEqual(codexc.get_active_alias(), "codex02")

    def test_cmd_rm_deletes_profile_launcher_and_reassigns_active(self):
        self._create_profile("codex01")
        self._create_profile("codex02")
        codexc.set_active_alias("codex01")
        codexc.set_default_alias("codex01")
        codexc.sync_launchers()

        os.makedirs(self.cache_dir, exist_ok=True)
        cache_file = os.path.join(self.cache_dir, "codex01.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write("{}")

        with mock.patch("builtins.input", return_value="s"):
            codexc.cmd_rm(argparse.Namespace(alias="codex01"))

        self.assertFalse(os.path.exists(os.path.join(self.homes_dir, "codex01")))
        self.assertFalse(os.path.exists(codexc.get_launcher_path(self.local_bin_dir, "codex01")))
        self.assertFalse(os.path.exists(cache_file))
        self.assertEqual(codexc.get_active_alias(), "codex02")
        self.assertEqual(codexc.get_default_alias(), "codex02")


class TestExportAndImport(CodexcTestCase):
    def test_export_single_alias_and_import_with_rename(self):
        prof_dir = self._create_profile("codex01", access_token="tok-export", account_id="acc-1")
        with open(os.path.join(prof_dir, "config.toml"), "w", encoding="utf-8") as f:
            f.write('model = "gpt-5"\n')

        bundle_path = os.path.join(self.root, "single.json")
        codexc.cmd_export(argparse.Namespace(alias="codex01", output=bundle_path))

        self.assertTrue(os.path.isfile(bundle_path))
        with open(bundle_path, "r", encoding="utf-8") as f:
            bundle = json.load(f)

        self.assertEqual(bundle["format"], "codexc-bundle-v1")
        self.assertIn("exported_at", bundle)
        self.assertEqual(len(bundle["accounts"]), 1)
        self.assertEqual(bundle["accounts"][0]["alias"], "codex01")
        self.assertEqual(bundle["accounts"][0]["auth"]["tokens"]["access_token"], "tok-export")
        self.assertIn('model = "gpt-5"', bundle["accounts"][0]["config_toml"])

        # Limpiar perfil original para probar importación limpia con --alias
        import shutil
        shutil.rmtree(prof_dir)
        codexc.cmd_import(argparse.Namespace(file=bundle_path, alias="codex09", overwrite=False))

        new_prof = os.path.join(self.homes_dir, "codex09")
        self.assertTrue(os.path.isfile(os.path.join(new_prof, "auth.json")))
        self.assertTrue(os.path.isfile(os.path.join(new_prof, "config.toml")))
        self.assertTrue(os.path.isfile(codexc.get_launcher_path(self.local_bin_dir, "codex09")))
        self.assertEqual(codexc.get_active_alias(), "codex09")
        self.assertEqual(codexc.get_default_alias(), "codex09")

    def test_import_rejects_existing_without_overwrite_and_updates_with_overwrite(self):
        prof_dir = self._create_profile("codex01", access_token="old-tok", account_id="acc-1")
        bundle_path = os.path.join(self.root, "bundle.json")
        with open(bundle_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "format": "codexc-bundle-v1",
                    "exported_at": "2026-11-19T00:00:00+00:00",
                    "accounts": [
                        {
                            "alias": "codex01",
                            "auth": {
                                "email": "dev1@gmail.com",
                                "tokens": {"access_token": "new-tok", "account_id": "acc-1"},
                            },
                            "config_toml": 'model = "o3"\n',
                        }
                    ],
                },
                f,
            )

        with self.assertRaises(SystemExit) as ctx:
            codexc.cmd_import(argparse.Namespace(file=bundle_path, alias=None, overwrite=False))
        self.assertEqual(ctx.exception.code, 1)

        codexc.cmd_import(argparse.Namespace(file=bundle_path, alias=None, overwrite=True))
        with open(os.path.join(prof_dir, "auth.json"), "r", encoding="utf-8") as f:
            updated = json.load(f)
        self.assertEqual(updated["tokens"]["access_token"], "new-tok")
        with open(os.path.join(prof_dir, "config.toml"), "r", encoding="utf-8") as f:
            self.assertIn('model = "o3"', f.read())

    def test_export_all_aliases_default_filename(self):
        self._create_profile("codex01", access_token="tok-1", account_id="acc-1")
        self._create_profile("codex02", access_token="tok-2", account_id="acc-2")

        old_cwd = os.getcwd()
        os.chdir(self.root)
        try:
            codexc.cmd_export(argparse.Namespace(alias=None, output=None))
        finally:
            os.chdir(old_cwd)

        default_bundle = os.path.join(self.root, "codexc-accounts-bundle.json")
        self.assertTrue(os.path.isfile(default_bundle))
        with open(default_bundle, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual([a["alias"] for a in data["accounts"]], ["codex01", "codex02"])


class TestWin32PlatformHelpers(unittest.TestCase):
    def test_win32_get_real_codex_bin_ignores_ps1_and_local_bin(self):
        with tempfile.TemporaryDirectory() as td:
            local_bin = os.path.join(td, "local_bin")
            npm_dir = os.path.join(td, "npm")
            os.makedirs(local_bin)
            os.makedirs(npm_dir)

            local_wrapper = os.path.join(local_bin, "codex.cmd")
            ps1_file = os.path.join(npm_dir, "codex.ps1")
            real_cmd = os.path.join(npm_dir, "codex.cmd")
            for p in (local_wrapper, ps1_file, real_cmd):
                with open(p, "w", encoding="utf-8") as f:
                    f.write("echo test\n")

            def fake_which(name):
                if name == "codex.exe":
                    return None
                if name == "codex.cmd":
                    return local_wrapper
                if name == "codex":
                    return ps1_file
                return None

            with mock.patch.object(platform_win32.shutil, "which", side_effect=fake_which):
                resolved = platform_win32.get_real_codex_bin(td, local_bin)

            self.assertEqual(resolved, real_cmd)
            self.assertFalse(resolved.lower().endswith(".ps1"))


if __name__ == "__main__":
    unittest.main()
