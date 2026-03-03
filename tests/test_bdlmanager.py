from core.bdlmanager import BDLManager

def test_get_config_data():
    bdl = BDLManager()
    config_data = bdl.get_config_data()
    assert config_data is not None
    assert "ModuloId" in config_data
    print("Config:", config_data)
