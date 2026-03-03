from core.bdrmanager import BDRManager

def test_read_config_table():
    bdr = BDRManager()
    dados = bdr.read("Config", "1=1")
    assert isinstance(dados, list)
    if dados:
        print("Primeiro registro:", dados[0])
    else:
        print("Nenhum registro encontrado.")
