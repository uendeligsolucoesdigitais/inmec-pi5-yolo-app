from core.configmanager import ConfigManager

def test_get_modulo_id():
    config = ConfigManager()
    modulo_id = config.get("ModuloId")
    assert modulo_id is not None
    print("ModuloId:", modulo_id)
