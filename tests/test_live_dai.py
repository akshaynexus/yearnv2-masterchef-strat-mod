# import brownie
# from brownie import Contract, StrategyLegacy, chain
# from useful_methods import genericStateOfVault, genericStateOfStrat
# import random


# def test_live_dai(accounts):

#     me = accounts.at("0x7495B77b15fCb52fbb7BCB7380335d819ce4c04B", force=True)
#     ygov = accounts.at("0xFEB4acf3df3cDEA7399794D0869ef76A6EfAff52", force=True)
#     dai_vault = Contract("0x19D3364A399d251E894aC732651be8B0E4e85001", owner=ygov)
#     sharerV4 = Contract("0xc491599b9a20c3a2f0a85697ee6d9434efa9f503")
#     iblevcomp = Contract("0x77b7CD137Dd9d94e7056f78308D7F65D2Ce68910", owner=ygov)
#     keeper = "0x7495B77b15fCb52fbb7BCB7380335d819ce4c04B"
#     masterchef = "0xd7fa57069E4767ddE13aD7970A562c43f03f8365"
#     reward = "0xf33121A2209609cAdc7349AcC9c40E41CE21c730"
#     router = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
#     pid = 3
#     strategy = StrategyLegacy.deploy(
#         dai_vault, masterchef, reward, router, pid, {"from": me},
#     )
#     # Remove iblevcomp to replace it with farmer strat
#     dai_vault.updateStrategyDebtRatio(iblevcomp, 0)
#     # Add strategy to vault
#     dai_vault.addStrategy(strategy, 5.5 * 100, 0, 1000)
#     # Remove funds from iblevcomp
#     iblevcomp.harvest()
#     strategy.harvest({"from": me})
#     # Get initial deposit
#     initialDeposit = strategy.estimatedTotalAssets()
#     for i in range(15):
#         waitBlock = random.randint(10, 50)
#         # print(f'\n----wait {waitBlock} blocks----')
#         chain.mine(waitBlock)
#         strategy.harvest({"from": me})
#         chain.sleep(waitBlock * 13)

#     strategy.harvest()
#     # check strategy made a profit
#     assert strategy.estimatedTotalAssets() > initialDeposit

#     # Assume farm is over,lets exit the farm
#     # Set emergencyexit
#     strategy.setEmergencyExit({"from": me})
#     # Call harvest to get funds out
#     strategy.harvest({"from": me})
#     # Check if the funds got out successfully
#     assert strategy.estimatedTotalAssets() == 0

#     # Lets add back iblev farming to vault
#     dai_vault.updateStrategyDebtRatio(iblevcomp, 5.5 * 100)
#     # we should harvest and get back the tvl on iblev
#     iblevcomp.harvest({"from": ygov})
#     assert iblevcomp.estimatedTotalAssets() > 0
