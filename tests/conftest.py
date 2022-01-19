import pytest
from brownie import config, Contract, accounts, Strategy

masterchef_addr = "0xE04C26444d37fE103B9cc8033c99b09D47056f51"
reward_addr = "0x911da02C1232A3c3E1418B834A311921143B04d7"
spookyswap_router = "0xF491e7B69E4244ad4002BC14e878a34207E38c29"
spiritswap_router = "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52"

fixtures = "currency", "whale", "reward", "masterchef", "pid", "router", "wantRouter"
params = [
    pytest.param(
        "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83",
        "0x5AA53f03197E08C4851CAD8C92c7922DA5857E5d",
        reward_addr,
        masterchef_addr,
        0,
        spiritswap_router,
        spookyswap_router,
        id="WFTM",
    ),
    # pytest.param(
    #     "0xf16e81dce15B08F326220742020379B855B87DF9",
    #     "0x314e9c5BbDCb8eA9d779b39718665a31e49F7A21",
    #     reward_addr,
    #     masterchef_addr,
    #     5,
    #     spiritswap_router,
    #     "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
    #     id="ICE",
    # ),
    # pytest.param(
    #     "0x841FAD6EAe12c286d1Fd18d1d525DFfA75C7EFFE",
    #     "0x1F0C5a9046f0db0e8b651Cd9E8e23ba4Efe4B86d",
    #     reward_addr,
    #     masterchef_addr,
    #     3,
    #     spiritswap_router,
    #     spookyswap_router,
    #     id="BOO",
    # ),
]


@pytest.fixture
def gov(accounts):
    yield accounts[0]


@pytest.fixture
def rewards(accounts):
    yield accounts[1]


@pytest.fixture
def currency(request, interface):
    yield interface.ERC20(request.param)


@pytest.fixture
def whale(request, currency):
    acc = accounts.at(request.param, force=True)
    yield acc


@pytest.fixture
def reward(request, interface):
    yield interface.ERC20(request.param)


@pytest.fixture
def masterchef(request, interface):
    yield interface.ChefLike(request.param)


# @pytest.fixture
# def dai(interface):
#     yield interface.ERC20("0x6B175474E89094C44Da98b954EedeAC495271d0F")


@pytest.fixture
def router(request):
    yield Contract(request.param)


@pytest.fixture
def wantRouter(request):
    yield Contract(request.param)


@pytest.fixture
def pid(request):
    yield request.param


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
def token(currency):
    yield currency


@pytest.fixture
def amount(accounts, token, whale):
    amount = 100 * 10 ** token.decimals()
    # In order to get some funds for the token you are about to use,
    # it impersonate an exchange address to use it's funds.
    reserve = whale
    token.transfer(accounts[0], amount, {"from": reserve})
    yield amount


@pytest.fixture
def weth(interface):
    token_address = "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"
    yield interface.ERC20(token_address)


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
    masterchef,
    reward,
    router,
    wantRouter,
    pid,
):
    strategy = strategist.deploy(
        Strategy, vault, masterchef, reward, router, wantRouter, pid
    )
    strategy.setKeeper(keeper)

    vault.addStrategy(strategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    yield strategy
