from pathlib import Path

from brownie import Strategy, accounts, config, network, project, web3, Contract
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
    #if we found no pid for want,raise valueError
    raise ValueError("No pid found for Want")

def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    print(f"You are using: 'dev' [{dev.address}]")

    if input("Is there a Vault for this strategy already? y/[N]: ").lower() == "y":
        vault = Vault.at(get_address("Deployed Vault: "))
        assert vault.apiVersion() == API_VERSION
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
    masterchef = "0xd7fa57069E4767ddE13aD7970A562c43f03f8365"
    reward = "0xf33121A2209609cAdc7349AcC9c40E41CE21c730"
    router = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"

    pid = get_pid(vault.token(),Contract.from_explorer(masterchef))
    print(pid)
    strategy = Strategy.deploy(vault, masterchef, reward,router,pid,{"from": dev}, publish_source=publish_source)