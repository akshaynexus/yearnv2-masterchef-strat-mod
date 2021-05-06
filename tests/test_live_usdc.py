# import brownie
# from brownie import Contract, StrategyLegacy, chain
# from useful_methods import genericStateOfVault, genericStateOfStrat
# import random


# def test_live_dai(accounts):

#     me = accounts.at("0x7495B77b15fCb52fbb7BCB7380335d819ce4c04B", force=True)
#     ygov = accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)
#     usdc_vault = Contract("0x5f18C75AbDAe578b483E5F43f12a39cF75b973a9", owner=ygov)
#     sharerV4 = Contract("0xc491599b9a20c3a2f0a85697ee6d9434efa9f503")
#     idleusdc = Contract("0x2E1ad896D3082C52A5AE7Af307131DE7a37a46a0", owner=ygov)
#     stratFarmer = Contract("0xFc403fd9E7A916eC38437807704e92236cA1f7A5", owner=me)
#     keeper = "0x7495B77b15fCb52fbb7BCB7380335d819ce4c04B"
#     masterchef = "0xd7fa57069E4767ddE13aD7970A562c43f03f8365"
#     reward = "0xf33121A2209609cAdc7349AcC9c40E41CE21c730"
#     router = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
#     pid = 2
#     tx = stratFarmer.cloneStrategy(
#         usdc_vault, me, sharerV4, keeper, masterchef, reward, router, pid, {"from": me}
#     )
#     strategy = StrategyLegacy.at(tx.events["Cloned"]["clone"])
#     # Remove idleusdc to replace it with farmer strat
#     usdc_vault.updateStrategyDebtRatio(idleusdc, 0)
#     # Add strategy to vault
#     usdc_vault.addStrategy(strategy, 500, 0, 1000)
#     # Remove funds from idleusdc
#     idleusdc.harvest()
#     strategy.harvest({"from": me})
#     # Get initial deposit
#     initialDeposit = strategy.estimatedTotalAssets()
#     for i in range(15):
#         waitBlock = random.randint(10, 20)
#         # print(f'\n----wait {waitBlock} blocks----')
#         chain.mine(waitBlock)
#         strategy.harvest({"from": me})
#         chain.sleep(waitBlock * 13)

#     strategy.harvest({"from": me})
#     # check strategy made a profit
#     assert strategy.estimatedTotalAssets() > initialDeposit

#     # Assume farm is over,lets exit the farm
#     # Set emergencyexit
#     strategy.setEmergencyExit({"from": me})
#     # Call harvest to get funds out
#     strategy.harvest({"from": me})
#     # Check if the funds got out successfully
#     assert strategy.estimatedTotalAssets() == 0

#     # Lets add back idleusdc farming to vault
#     usdc_vault.updateStrategyDebtRatio(idleusdc, 500)
#     # we should harvest and get back the tvl on idleusdc
#     idleusdc.harvest({"from": ygov})
#     assert idleusdc.estimatedTotalAssets() > 0
