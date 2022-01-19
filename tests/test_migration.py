import brownie
from brownie import Contract
import pytest
import conftest as config

# TODO: Add tests that show proper migration of the strategy to a newer one
#       Use another copy of the strategy to simulate the migration
#       Show that nothing is lost!


@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
def test_migration(
    token,
    vault,
    chain,
    strategy,
    Strategy,
    strategist,
    whale,
    gov,
    masterchef,
    reward,
    router,
    wantRouter,
    pid,
):
    chain.snapshot()
    with brownie.reverts("Strategy already initialized"):
        strategy.initialize(
            vault,
            strategist,
            strategist,
            strategist,
            masterchef,
            reward,
            router,
            wantRouter,
            pid,
        )

    # Deposit to the vault and harvest
    amount = 110000 * 1e18
    bbefore = token.balanceOf(whale)

    token.approve(vault.address, amount, {"from": whale})
    vault.deposit(amount, {"from": whale})

    strategy.harvest()

    tx = strategy.cloneStrategy(
        vault,
        strategist,
        strategist,
        strategist,
        masterchef,
        reward,
        router,
        wantRouter,
        pid,
    )

    # migrate to a new strategy
    new_strategy = Strategy.at(tx.return_value)
    strategy.harvest()
    chain.mine(20)
    chain.sleep(2000)
    strategy.harvest({"from": gov})

    vault.migrateStrategy(strategy, new_strategy, {"from": gov})
    assert new_strategy.estimatedTotalAssets() >= amount
    assert strategy.estimatedTotalAssets() == 0

    new_strategy.harvest({"from": gov})

    chain.mine(20)
    chain.sleep(2000)
    new_strategy.harvest({"from": gov})
    chain.sleep(60000)
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) > bbefore
    chain.revert()
