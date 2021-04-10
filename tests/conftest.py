import pytest
from brownie import config, Contract


@pytest.fixture
def gov(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def whale(accounts):
    # big binance7 wallet
    # acc = accounts.at('0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8', force=True)
    # big binance8 wallet
    acc = accounts.at("0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503", force=True)

    # lots of weth account
    # wethAcc = accounts.at("0x767Ecb395def19Ab8d1b2FCc89B3DDfBeD28fD6b", force=True)
    # weth.approve(acc, 2 ** 256 - 1, {"from": wethAcc})
    # weth.transfer(acc, weth.balanceOf(wethAcc), {"from": wethAcc})

    # assert weth.balanceOf(acc) > 0
    yield acc


@pytest.fixture
def dai(interface):
    yield interface.ERC20("0x6B175474E89094C44Da98b954EedeAC495271d0F")


@pytest.fixture
def bag_masterchef(interface):
    yield interface.ChefLike("0xd7fa57069E4767ddE13aD7970A562c43f03f8365")


@pytest.fixture
def bag(interface):
    yield interface.ERC20("0xf33121A2209609cAdc7349AcC9c40E41CE21c730")


@pytest.fixture
def router():
    yield Contract("0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D")


@pytest.fixture
def pid():
    yield 3


@pytest.fixture
def guardian(accounts):
    yield accounts[2]


@pytest.fixture
def management(accounts):
    yield accounts[3]


@pytest.fixture
def strategist(accounts):
    yield accounts[4]


@pytest.fixture
def keeper(accounts):
    yield accounts[5]


@pytest.fixture
def token(dai):
    yield dai


@pytest.fixture
def amount(accounts, token):
    amount = 100 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = accounts.at("0xd551234ae421e3bcba99a0da6d736074f22192ff", force=True)
    token.transfer(accounts[0], amount, {"from": reserve})
    yield amount


@pytest.fixture
def weth():
    token_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    yield Contract(token_address)


@pytest.fixture
def weth_amout(gov, weth):
    weth_amout = 10 ** weth.decimals()
    gov.transfer(weth, weth_amout)
    yield weth_amout


@pytest.fixture
def live_vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    yield Vault.at("0xE14d13d8B3b85aF791b2AADD661cDBd5E6097Db1")


@pytest.fixture
def live_strat(Strategy):
    yield Strategy.at("0xd4419DDc50170CB2DBb0c5B4bBB6141F3bCc923B")


@pytest.fixture
def live_vault_weth(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    yield Vault.at("0xa9fE4601811213c340e850ea305481afF02f5b28")


@pytest.fixture
def live_strat_weth(Strategy):
    yield Strategy.at("0xDdf11AEB5Ce1E91CF19C7E2374B0F7A88803eF36")


@pytest.fixture
def vault(pm, gov, rewards, guardian, management, token):
    Vault = pm(config["dependencies"][0]).Vault
    vault = guardian.deploy(Vault)
    vault.initialize(token, gov, rewards, "", "", guardian)
    vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
    vault.setManagement(management, {"from": gov})
    yield vault


@pytest.fixture
def strategy(
    strategist,
    keeper,
    vault,
    token,
    weth,
    Strategy,
    gov,
    bag_masterchef,
    bag,
    router,
    pid,
):
    strategy = strategist.deploy(Strategy, vault, bag_masterchef, bag, router, pid)
    strategy.setKeeper(keeper)

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy
