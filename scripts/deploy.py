from pathlib import Path

from brownie import Strategy, config, project, network, Contract, accounts

from eth_utils import is_checksum_address
import click

API_VERSION = config["dependencies"][0].split("@")[-1]
Vault = project.load(
    Path.home() / ".brownie" / "packages" / config["dependencies"][0]
).Vault

masterchef_addr = "0xE04C26444d37fE103B9cc8033c99b09D47056f51"
spookyswap_router = "0xF491e7B69E4244ad4002BC14e878a34207E38c29"
spiritswap_router = "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52"

def get_address(msg: str) -> str:
    while True:
        val = input(msg)
        if is_checksum_address(val):
            return val
        else:
            addr = web3.ens.address(val)
            if addr:
                print(f"Found ENS '{val}' [{addr}]")
                return addr
        print(f"I'm sorry, but '{val}' is not a checksummed address or ENS")


def get_pid(want, chef):
    for i in range(chef.poolLength()):
        if chef.poolInfo(i)[0] == want:
            return i
    raise ValueError("No pid found for Want")

def getRouter(pid):
    if pid == 0:
        return spiritswap_router
    elif pid == 5:
        return spiritswap_router
    elif pid == 3:
        return spookyswap_router

def getWantRouter(pid):
    if pid == 0:
        return spookyswap_router
    elif pid == 5:
        return spiritswap_router
    elif pid == 3:
        return spookyswap_router



EXPERIMENTAL_DEPLOY = False
WANT_TOKEN = "0xdc301622e621166BD8E82f2cA0A26c13Ad0BE355"


def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    print(f"You are using: 'dev' [{dev.address}]")
    if input("Is there a Vault for this strategy already? y/[N]: ").lower() == "y":
        vault = Vault.at(get_address("Deployed Vault: "))
        assert vault.apiVersion() == API_VERSION
    elif EXPERIMENTAL_DEPLOY:
        vaultRegistry = IVaultRegistry(VAULT_REGISTRY)
        # Deploy and get Vault deployment address
        expVaultTx = vaultRegistry.newExperimentalVault(
            WANT_TOKEN,
            STRATEGIST_ADDR,
            STRATEGIST_MULTISIG,
            TREASURY,
            "",
            "",
            {"from": dev},
        )
        vault = Vault.at(expVaultTx.return_value)
    else:
        # Deploy vault
        vault = Vault.deploy({"from": dev})
        vault.initialize(
            WANT_TOKEN,  # OneInch token as want token
            dev,  # governance
            dev,  # rewards
            "",  # nameoverride
            "",  # symboloverride
            {"from": dev},
        )
        print(API_VERSION)
        assert vault.apiVersion() == API_VERSION

    print(
        f"""
    Strategy Parameters

       api: {API_VERSION}
     token: {vault.token()}
      name: '{vault.name()}'
    symbol: '{vault.symbol()}'
    """
    )
    publish_source = click.confirm("Verify source on etherscan?")
    if input("Deploy Strategy? y/[N]: ").lower() != "y":
        return

    masterchef = masterchef_addr
    pid = get_pid(vault.token(), Contract.from_explorer(masterchef))
    print(pid)
    reward = "0x911da02C1232A3c3E1418B834A311921143B04d7"
    router = getRouter(pid)
    wantRouter = getWantRouter(pid)

    legacyVault = vault.apiVersion() == "0.3.0"

    if not legacyVault:
        strategy = Strategy.deploy(
            vault,
            masterchef,
            reward,
            router,
            wantRouter,
            pid,
            {"from": dev},
            publish_source=publish_source,
        )
        vault.setPerformanceFee(2000, {"from": dev})
        # add strat to vault
        vault.addStrategy(strategy, 10000, 0, 2 ** 256 - 1, 0, {"from": dev})
        # Set deposit limit to 1008 1INCH tokens,Approx 50K
        vault.setDepositLimit(100_000_000 * 1e18, {"from": dev})
    else:
        strategy = StrategyLegacy.deploy(
            vault,
            masterchef,
            reward,
            router,
            pid,
            {"from": dev},
            publish_source=publish_source,
        )
