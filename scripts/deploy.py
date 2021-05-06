from pathlib import Path

from brownie import Strategy, StrategyLegacy, config, project, network, Contract

from eth_utils import is_checksum_address
import click

API_VERSION = config["dependencies"][0].split("@")[-1]
Vault = project.load(
    Path.home() / ".brownie" / "packages" / config["dependencies"][0]
).Vault


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


def getWantRouter(pid):
    if pid == 1:
        return "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52"
    elif pid == 5:
        return "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506"
    elif pid == 3:
        return "0xF491e7B69E4244ad4002BC14e878a34207E38c29"


def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    print(f"You are using: 'dev' [{dev.address}]")
    if input("Is there a Vault for this strategy already? y/[N]: ").lower() == "y":
        vault = Vault.at(get_address("Deployed Vault: "))
        # assert vault.apiVersion() == API_VERSION
    else:
        print("You should deploy one vault using scripts from Vault project")
        return  # TODO: Deploy one using scripts from Vault project
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

    masterchef = "0x78e9D247541ff7c365b50D2eE0defdd622016498"
    pid = get_pid(vault.token(), Contract.from_explorer(masterchef))
    print(pid)
    reward = "0x181F3F22C9a751E2ce673498A03E1FDFC0ebBFB6"
    router = "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52"
    wantRouter = getWantRouter(pid)

    legacyVault = vault.apiVersion() == "0.3.0"

    if not legacyVault:
        strategy = Strategy.deploy(
            vault,
            masterchef,
            reward,
            router,
            pid,
            {"from": dev},
            publish_source=publish_source,
        )
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
