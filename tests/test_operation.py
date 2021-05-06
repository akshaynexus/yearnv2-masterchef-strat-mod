import brownie
from brownie import Contract, chain
from useful_methods import genericStateOfVault, genericStateOfStrat
import random
import pytest
import conftest as config


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_apr(accounts, token, vault, strategy, chain, strategist, whale):
    strategist = accounts[0]
    chain.snapshot()

    amount = 1 * 1e18
    # Deposit to the vault
    token.approve(vault, amount, {"from": whale})
    vault.deposit(amount, {"from": whale})
    assert token.balanceOf(vault.address) == amount

    # harvest
    strategy.harvest()
    startingBalance = vault.totalAssets()
    for i in range(2):

        waitBlock = 50
        # print(f'\n----wait {waitBlock} blocks----')
        chain.mine(waitBlock)
        chain.sleep(waitBlock * 13)
        # print(f'\n----harvest----')
        strategy.harvest({"from": strategist})

        # genericStateOfStrat(strategy, currency, vault)
        # genericStateOfVault(vault, currency)

        profit = (vault.totalAssets() - startingBalance) / 1e18
        strState = vault.strategies(strategy)
        totalReturns = strState[7]
        totaleth = totalReturns / 1e18
        # print(f'Real Profit: {profit:.5f}')
        difff = profit - totaleth
        # print(f'Diff: {difff}')

        blocks_per_year = 2_252_857
        assert startingBalance != 0
        time = (i + 1) * waitBlock
        assert time != 0
        apr = (totalReturns / startingBalance) * (blocks_per_year / time)
        assert apr > 0
        # print(apr)
        print(f"implied apr: {apr:.8%}")
    chain.revert()


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_normal_activity(accounts, token, vault, strategy, strategist, whale, chain):

    amount = 1 * 1e18
    bbefore = token.balanceOf(whale)
    chain.snapshot()

    # Deposit to the vault
    token.approve(vault, amount, {"from": whale})
    vault.deposit(amount, {"from": whale})
    assert token.balanceOf(vault.address) == amount

    # harvest
    strategy.harvest()
    for i in range(15):
        waitBlock = random.randint(10, 50)

    strategy.harvest()
    chain.sleep(60000)
    # withdrawal
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) > bbefore
    genericStateOfStrat(strategy, token, vault)
    genericStateOfVault(vault, token)
    chain.revert()


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_emergency_withdraw(
    accounts, token, vault, strategy, strategist, whale, chain, pid
):
    chain.snapshot()

    amount = 1 * 1e18
    bbefore = token.balanceOf(whale)

    # Deposit to the vault
    token.approve(vault, amount, {"from": whale})
    vault.deposit(amount, {"from": whale})
    assert token.balanceOf(vault.address) == amount

    # harvest deposit into staking contract
    strategy.harvest()
    assert token.balanceOf(strategy) == 0
    strategy.emergencyWithdrawal(pid, {"from": accounts[0]})
    assert token.balanceOf(strategy) >= amount
    chain.revert()


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_emergency_exit(accounts, token, vault, strategy, strategist, amount):
    chain.snapshot()
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": accounts[0]})
    vault.deposit(amount, {"from": accounts[0]})
    strategy.harvest()

    # harvest should have transfered tokens to strat and staked it
    assert token.balanceOf(strategy.address) == 0

    # set emergency and exit
    strategy.setEmergencyExit()
    strategy.harvest()
    assert token.balanceOf(strategy.address) < amount
    chain.revert()


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_profitable_harvest(accounts, token, vault, strategy, strategist, amount):
    chain.snapshot()
    # Deposit to the vault
    token.approve(vault.address, amount, {"from": accounts[0]})
    vault.deposit(amount, {"from": accounts[0]})
    assert token.balanceOf(vault.address) == amount

    # harvest
    strategy.harvest()
    # harvest should have transfered tokens to strat and staked it
    assert token.balanceOf(strategy.address) == 0
    # You should test that the harvest method is capable of making a profit.
    # TODO: uncomment the following lines.
    # strategy.harvest()
    # chain.sleep(3600 * 24)
    # assert token.balanceOf(strategy.address) > amount
    chain.revert()


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)

def test_change_debt(gov, token, vault, strategy, strategist, amount):
    chain.snapshot()
    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": gov})
    vault.deposit(amount, {"from": gov})
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    strategy.harvest()

    assert token.balanceOf(vault.address) == amount / 2

    vault.updateStrategyDebtRatio(strategy.address, 10_000, {"from": gov})
    strategy.harvest()
    assert strategy.estimatedTotalAssets() >= amount
    chain.revert()

    # In order to pass this tests, you will need to implement prepareReturn.
    # TODO: uncomment the following lines.
    # vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    # assert token.balanceOf(strategy.address) == amount / 2

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_triggers(gov, vault, strategy, token, amount):
    chain.snapshot()

    # Deposit to the vault and harvest
    token.approve(vault.address, amount, {"from": gov})
    vault.deposit(amount, {"from": gov})
    vault.updateStrategyDebtRatio(strategy.address, 5_000, {"from": gov})
    strategy.harvest()

    strategy.harvestTrigger(0)
    strategy.tendTrigger(0)
    chain.revert()
