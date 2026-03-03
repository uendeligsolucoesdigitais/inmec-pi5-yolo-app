import os
import time
import sqlite3
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple
from config.config import ConfigManagerConfig
CFG = ConfigManagerConfig()

# Padrões que queremos garantir no config.xml
DEFAULT_OVERLAY_CONFIG = CFG.default_overlay

class ConfigManager:
    _sync_done = False
    def __init__(self, path="config/config.xml", sync: bool = True):
        self.path = path if path else CFG.default_xml_path
        self.dados = {}
        self._carregar()
        # Garante que as chaves padrão existam no XML (se faltarem, cria agora)
        self.ensure_defaults(DEFAULT_OVERLAY_CONFIG)
        if sync and not ConfigManager._sync_done:
            ConfigManager._sync_done = True
            try:
                self._sync_from_bdr_or_bdl()
            except Exception:
                pass

    def _carregar(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.path}")
        tree = ET.parse(self.path)
        root = tree.getroot()
        config = root.find(CFG.xml_root_tag)
        self.dados = {}
        for elem in config:
            self.dados[elem.tag] = elem.text

    def get_tudo(self):
        return self.dados

    def get(self, chave):
        return self.dados.get(chave)

    def set(self, chave, valor):
        tree = ET.parse(self.path)
        root = tree.getroot()
        config = root.find(CFG.xml_root_tag)
        encontrado = False
        for elem in config:
            if elem.tag == chave:
                elem.text = valor
                encontrado = True
                break
        if not encontrado:
            ET.SubElement(config, chave).text = valor
        tree.write(self.path, encoding=CFG.xml_encoding, xml_declaration=True)
        self._carregar()

    def ensure_defaults(self, defaults: dict):
        """
        Garante que cada chave de 'defaults' exista na config.
        Se não existir (ou estiver vazia), escreve o valor padrão.
        Obs.: como 'set' já grava e recarrega o XML, não é necessário 'save' separado.
        Retorna True se houve alguma alteração, caso contrário False.
        """
        changed = False
        for key, val in defaults.items():
            cur = self.get(key)
            if cur is None or str(cur).strip() == "":
                try:
                    self.set(key, val)  # 'set' já persiste e recarrega
                    changed = True
                except Exception as e:
                    print(f"[⚠️] Falha ao definir padrão '{key}': {e}")
        return changed

    # =========================
    # SincronizaÃ§Ã£o XML <-> BDR/BDL
    # =========================
    def _sync_from_bdr_or_bdl(self):
        sync_keys = tuple(CFG.sync_keys)
        self._ensure_xml_keys(sync_keys + (CFG.tentativas_key,))

        self._status_msg("[🔌] Acessando BDR...")
        bdr_data, bdr_ok = self._fetch_bdr_config(sync_keys)
        if bdr_ok:
            if bdr_data:
                self._update_xml_values(bdr_data)
                self._sync_bdl_from_bdr(bdr_data)
                self._status_msg("[✅] Atualizações carregadas no BDL e no config.xml.")
            return

        tentativas = self._increment_tentativas()
        if tentativas is not None and tentativas > 3:
            self._block_on_excess_tentativas()
            return
        if tentativas is not None and tentativas <= 3:
            bdl_data = self._fetch_bdl_config(sync_keys)
            if bdl_data:
                self._update_xml_values(bdl_data)

    def _fetch_bdr_config(self, keys: Tuple[str, ...]) -> Tuple[Dict[str, Any], bool]:
        host = self.dados.get("host_name")
        port = self.dados.get("dbport")
        user = self.dados.get("user_name")
        password = self.dados.get("user_password")
        dbname = self.dados.get("db_name")
        modulo_id = self.dados.get("ModuloId")
        if not (host and port and user and password and dbname and modulo_id):
            return {}, False

        last_err = None
        for _ in range(CFG.bdr_retry_count):
            try:
                import mysql.connector
                conn = mysql.connector.connect(
                    host=host,
                    port=int(port),
                    user=user,
                    password=password,
                    database=dbname,
                )
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM Config WHERE ModuloId = %s", (modulo_id,))
                row = cur.fetchone() or {}
                cur.close()
                conn.close()

                data = {k: row.get(k) for k in keys if k in row}
                return data, True
            except Exception as e:
                last_err = e
                time.sleep(CFG.bdr_retry_delay_s)

        _ = last_err
        return {}, False

    def _fetch_bdl_config(self, keys: Tuple[str, ...]) -> Dict[str, Any]:
        try:
            db_path = os.path.join(
                str(self.dados.get("db_path_local") or ""),
                str(self.dados.get("db_name_local") or ""),
            )
            if not os.path.isfile(db_path):
                self._block_on_bdl_inaccessible(f"Arquivo BDL nÃ£o encontrado: {db_path}")
                return {}
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            modulo_id = self.dados.get("ModuloId")
            cur.execute("SELECT * FROM Config WHERE ModuloId = ?", (modulo_id,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if not row:
                return {}
            return {k: row[k] for k in keys if k in row.keys()}
        except Exception as e:
            self._block_on_bdl_inaccessible(f"Falha ao acessar BDL: {e}")
            return {}

    def _sync_bdl_from_bdr(self, data: Dict[str, Any]):
        try:
            db_path = os.path.join(
                str(self.dados.get("db_path_local") or ""),
                str(self.dados.get("db_name_local") or ""),
            )
            if not db_path:
                return
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            self._ensure_bdl_columns(cur, "Config", ["ModuloId"] + list(data.keys()))

            modulo_id = self.dados.get("ModuloId")
            cur.execute("SELECT 1 FROM Config WHERE ModuloId = ? LIMIT 1", (modulo_id,))
            exists = cur.fetchone() is not None

            if exists:
                set_cols = ", ".join([f"{k} = ?" for k in data.keys()])
                values = [self._safe_str(v) for v in data.values()] + [modulo_id]
                cur.execute(f"UPDATE Config SET {set_cols} WHERE ModuloId = ?", values)
            else:
                cols = ["ModuloId"] + list(data.keys())
                placeholders = ", ".join(["?"] * len(cols))
                values = [modulo_id] + [self._safe_str(v) for v in data.values()]
                cur.execute(f"INSERT INTO Config ({', '.join(cols)}) VALUES ({placeholders})", values)

            conn.commit()
            conn.close()
        except Exception:
            pass

    def _ensure_bdl_columns(self, cur: sqlite3.Cursor, table: str, columns: list):
        cur.execute(f"PRAGMA table_info({table})")
        existing = {row[1] for row in cur.fetchall()}
        for col in columns:
            if col and col not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")

    def _ensure_xml_keys(self, keys: Tuple[str, ...]):
        tree = ET.parse(self.path)
        root = tree.getroot()
        config = root.find(CFG.xml_root_tag)
        changed = False
        for key in keys:
            if key not in self.dados:
                ET.SubElement(config, key).text = ""
                changed = True
        if changed:
            tree.write(self.path, encoding=CFG.xml_encoding, xml_declaration=True)
            self._carregar()

    def _update_xml_values(self, values: Dict[str, Any]):
        if not values:
            return
        tree = ET.parse(self.path)
        root = tree.getroot()
        config = root.find(CFG.xml_root_tag)
        changed = False
        for key, val in values.items():
            if val is None:
                val = ""
            found = False
            for elem in config:
                if elem.tag == key:
                    elem.text = self._safe_str(val)
                    found = True
                    changed = True
                    break
            if not found:
                ET.SubElement(config, key).text = self._safe_str(val)
                changed = True
        if changed:
            tree.write(self.path, encoding=CFG.xml_encoding, xml_declaration=True)
            self._carregar()

    def _increment_tentativas(self) -> Optional[int]:
        key = CFG.tentativas_key
        cur = self.dados.get(key)
        try:
            cur_int = int(str(cur).strip()) if cur is not None and str(cur).strip() != "" else 0
        except Exception:
            cur_int = 0
        new_val = cur_int + 1
        self._update_xml_values({key: str(new_val)})
        return new_val

    def _block_on_excess_tentativas(self):
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            import sys
            app = QApplication.instance() or QApplication(sys.argv)
            msg = QMessageBox()
            msg.setWindowTitle("Erro de Licenciamento")
            msg.setText("A licenÃ§a nÃ£o pode ser validada.")
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            QApplication.quit()
            sys.exit(1)
        except Exception:
            raise RuntimeError("A licenÃ§a nÃ£o pode ser validada.")

    def _block_on_bdl_inaccessible(self, detalhe: str):
        msg_text = "Banco de Dados Local estÃ¡ inacessÃ­vel."
        self._status_msg(f"[âŒ] {msg_text} {detalhe}")
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            import sys
            app = QApplication.instance() or QApplication(sys.argv)
            msg = QMessageBox()
            msg.setWindowTitle("Erro de Banco de Dados Local")
            msg.setText(msg_text)
            msg.setIcon(QMessageBox.Critical)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()
            QApplication.quit()
            sys.exit(1)
        except Exception:
            raise RuntimeError(msg_text)

    def _status_msg(self, text: str, ms: int = 5000):
        print(text)
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                return
            win = app.activeWindow()
            if win and hasattr(win, "statusBar"):
                sb = win.statusBar()
                if sb:
                    sb.showMessage(text, ms)
                    return
            if win and hasattr(win, "status_bar"):
                sb = getattr(win, "status_bar")
                if sb and hasattr(sb, "showMessage"):
                    sb.showMessage(text, ms)
        except Exception:
            pass

    @staticmethod
    def _safe_str(value: Any) -> str:
        if value is None:
            return ""
        return str(value)
