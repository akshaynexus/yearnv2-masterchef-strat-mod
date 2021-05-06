import pytest
import brownie
from brownie import Wei, accounts, Contract, config
import conftest as config

@pytest.mark.parametrize(config.fixtures, config.params, indirect=True)
@pytest.mark.require_network("ftm-main-fork")
def test_clone(
    chain,
    gov,
    strategist,
    rewards,
    keeper,
    strategy,
    Strategy,
    vault,
    masterchef,
    reward,
    router,
    whale,
    wantRouter,
    pid,
):
    chain.snapshot()
    # Shouldn't be able to call initialize again
    with brownie.reverts():
        strategy.initialize(
            vault,
            strategist,
            rewards,
            keeper,
            masterchef,
            reward,
            router,
            wantRouter,
            pid,
            {"from": gov},
        )

    # Clone the strategy
    tx = strategy.cloneStrategy(
        vault,
        strategist,
        rewards,
        keeper,
        masterchef,
        reward,
        router,
        wantRouter,
        pid,
        {"from": gov},
    )
    new_strategy = Strategy.at(tx.return_value)

    # Shouldn't be able to call initialize again
    with brownie.reverts():
        new_strategy.initialize(
            vault,
            strategist,
            rewards,
            keeper,
            masterchef,
            reward,
            router,
            wantRouter,
            pid,
            {"from": gov},
        )
    chain.revert()

    # TODO: do a migrate and test a harvest
