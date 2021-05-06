// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "./BaseStrategyLegacy.sol";
import "@openzeppelin/contracts/math/Math.sol";

import "./Interfaces/UniswapInterfaces/IUniswapV2Router02.sol";

interface ChefLike {
    struct UserInfo {
        uint256 amount; // How many LP tokens the user has provided.
        uint256 rewardDebt; // Reward debt.
    }

    struct PoolInfo {
        address token; // Address of staking token contract.
        uint256 allocPoint; // How many allocation points assigned to this pool.
        uint256 lastRewardTime; // Last block number that distribution occurs.
        uint256 accESTPerShare; // Accumulated reward tokens per share, times 1e24. See below.
        // uint16 earlyWithdrawalFeeBP; // Early withdrawal fee in basis points
    }

    function deposit(uint256 _pid, uint256 _amount) external;

    function withdraw(uint256 _pid, uint256 _amount) external;

    function emergencyWithdraw(uint256 _pid) external;

    function poolInfo(uint256 _pid) external view returns (PoolInfo memory);

    function userInfo(uint256 _pid, address user)
        external
        view
        returns (UserInfo memory);

    function harvest(uint256 _pid) external;

    function pendingEST(uint256 _pid, address _user)
        external
        view
        returns (uint256);
}

interface IERC20Extended {
    function decimals() external view returns (uint8);

    function name() external view returns (string memory);

    function symbol() external view returns (string memory);
}

//This strategy is for 0.3.0 Vaults
contract StrategyLegacy is BaseStrategyLegacy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    ChefLike public masterchef;
    IERC20 public reward;

    address private constant spookyswapRouter =
        address(0xF491e7B69E4244ad4002BC14e878a34207E38c29);
    address private constant sushiswapRouter =
        address(0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506);
    address private constant spiritswapRouter =
        address(0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52);

    address private constant wftm =
        address(0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83);

    //This will be the router we convert our rewards to ftm in
    IUniswapV2Router02 public rewardRouter;
    //This will be the router we use to convert wftm to want,this is for coins like boo or ice where liq is better on sushi or spooky than spiritswap
    IUniswapV2Router02 public wantRouter;

    uint256 public pid;
    uint256 public minProfit;

    address[] public path;

    bool public bypassWithdrawFee;
    bool public harvestOnLiq;
    bool public swapRewardViaSecondaryRouter;

    event Cloned(address indexed clone);

    modifier onlyGuardians() {
        require(
            msg.sender == strategist ||
                msg.sender == governance() ||
                msg.sender == vault.guardian() ||
                msg.sender == vault.management(),
            "!authorized"
        );
        _;
    }

    constructor(
        address _vault,
        address _masterchef,
        address _reward,
        address _router,
        address _wantRouter,
        uint256 _pid
    ) public BaseStrategyLegacy(_vault) {
        _initializeStrat(_masterchef, _reward, _router, _wantRouter, _pid);
    }

    function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _masterchef,
        address _reward,
        address _router,
        address _wantRouter,
        uint256 _pid
    ) external {
        //note: initialise can only be called once. in _initialize in BaseStrategy we have: require(address(want) == address(0), "Strategy already initialized");
        _initialize(_vault, _strategist, _rewards, _keeper);
        _initializeStrat(_masterchef, _reward, _router, _wantRouter, _pid);
    }

    function checkRouter(address _router) internal view returns (bool) {
        return
            _router == spookyswapRouter ||
            _router == sushiswapRouter ||
            _router == spiritswapRouter;
    }

    function _initializeStrat(
        address _masterchef,
        address _reward,
        address _router,
        address _wantRouter,
        uint256 _pid
    ) internal {
        require(
            address(rewardRouter) == address(0),
            "Masterchef Strategy already initialized"
        );
        require(checkRouter(_router), "incorrect rewardRouter");
        require(checkRouter(_wantRouter), "incorrect wantRouter");

        // You can set these parameters on deployment to whatever you want
        minReportDelay = 30 minutes;
        maxReportDelay = 6300;
        profitFactor = 1500;
        debtThreshold = 1_000_000 * 1e18;
        masterchef = ChefLike(_masterchef);
        reward = IERC20(_reward);
        rewardRouter = IUniswapV2Router02(_router);
        wantRouter = IUniswapV2Router02(_wantRouter);
        pid = _pid;
        path = getTokenOutPath(_reward, address(want));
        harvestOnLiq = true;
        swapRewardViaSecondaryRouter = _router != _wantRouter;
        require(address(want) == masterchef.poolInfo(pid).token, "wrong pid");
        minProfit = 30 ether;
        want.safeApprove(_masterchef, type(uint256).max);
        reward.safeApprove(_router, type(uint256).max);
        if (swapRewardViaSecondaryRouter)
            IERC20(wftm).safeApprove(_wantRouter, type(uint256).max);
        bypassWithdrawFee = false;
    }

    function cloneStrategy(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _masterchef,
        address _reward,
        address _router,
        address _wantRouter,
        uint256 _pid
    ) external returns (address newStrategy) {
        // Copied from https://github.com/optionality/clone-factory/blob/master/contracts/CloneFactory.sol
        bytes20 addressBytes = bytes20(address(this));

        assembly {
            // EIP-1167 bytecode
            let clone_code := mload(0x40)
            mstore(
                clone_code,
                0x3d602d80600a3d3981f3363d3d373d3d3d363d73000000000000000000000000
            )
            mstore(add(clone_code, 0x14), addressBytes)
            mstore(
                add(clone_code, 0x28),
                0x5af43d82803e903d91602b57fd5bf30000000000000000000000000000000000
            )
            newStrategy := create(0, clone_code, 0x37)
        }

        StrategyLegacy(newStrategy).initialize(
            _vault,
            _strategist,
            _rewards,
            _keeper,
            _masterchef,
            _reward,
            _router,
            _wantRouter,
            _pid
        );

        emit Cloned(newStrategy);
    }

    function setRouter(address _router) public onlyGovernance {
        require(checkRouter(_router), "incorrect rewardRouter");
        reward.safeApprove(address(rewardRouter), 0);
        rewardRouter = IUniswapV2Router02(_router);
        reward.safeApprove(_router, type(uint256).max);
    }

    function setWantRouter(address _router) public onlyGovernance {
        require(checkRouter(_router), "incorrect rewardRouter");
        IERC20(wftm).safeApprove(address(wantRouter), 0);
        wantRouter = IUniswapV2Router02(_router);
        IERC20(wftm).safeApprove(_router, type(uint256).max);
        swapRewardViaSecondaryRouter = address(rewardRouter) != _router;
    }

    function updateMinProfit(uint256 _minProfitNew) public onlyStrategist {
        minProfit = _minProfitNew;
    }

    function toggleBypassWithdrawFee() public onlyAuthorized {
        bypassWithdrawFee = !bypassWithdrawFee;
    }

    function getTokenOutPath(address _token_in, address _token_out)
        internal
        view
        returns (address[] memory _path)
    {
        bool is_wftm =
            _token_in == address(wftm) || _token_out == address(wftm);
        _path = new address[](is_wftm ? 2 : 3);
        _path[0] = _token_in;
        if (is_wftm) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(wftm);
            _path[2] = _token_out;
        }
    }

    function setPath(address[] calldata _path) public onlyGuardians {
        path = _path;
    }

    // ******** OVERRIDE THESE METHODS FROM BASE CONTRACT ************

    function name() external view override returns (string memory) {
        return
            string(
                abi.encodePacked(
                    "EsterMasterchef",
                    IERC20Extended(address(want)).name()
                )
            );
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        uint256 deposited = masterchef.userInfo(pid, address(this)).amount;
        return want.balanceOf(address(this)).add(deposited);
    }

    function pendingReward() public view returns (uint256) {
        return masterchef.pendingEST(pid, address(this));
    }

    function quote(
        address token_in,
        address token_out,
        uint256 amount_in
    ) internal view returns (uint256) {
        if (amount_in < 10 wei) return 0;
        uint256[] memory amounts =
            rewardRouter.getAmountsOut(
                amount_in,
                getTokenOutPath(token_in, token_out)
            );
        return amounts[amounts.length - 1];
    }

    function harvestTrigger(uint256 callCostInWei)
        public
        view
        virtual
        override
        returns (bool)
    {
        return
            super.harvestTrigger(callCostInWei) ||
            quote(address(reward), wftm, pendingReward().mul(10).div(100)) >=
            minProfit;
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        if (pendingReward() > 0) masterchef.deposit(pid, 0);

        _sell();

        uint256 assets = estimatedTotalAssets();
        uint256 wantBal = want.balanceOf(address(this));

        uint256 debt = vault.strategies(address(this)).totalDebt;

        if (assets >= debt) {
            _debtPayment = _debtOutstanding;
            _profit = assets.sub(debt);

            uint256 amountToFree = _profit.add(_debtPayment);

            if (amountToFree > 0 && wantBal < amountToFree) {
                liquidatePosition(amountToFree);

                uint256 newLoose = want.balanceOf(address(this));

                //if we dont have enough money adjust _debtOutstanding and only change profit if needed
                if (newLoose < amountToFree) {
                    if (_profit > newLoose) {
                        _profit = newLoose;
                        _debtPayment = 0;
                    } else {
                        _debtPayment = Math.min(
                            newLoose - _profit,
                            _debtPayment
                        );
                    }
                }
            }
        } else {
            //serious loss should never happen but if it does lets record it accurately
            _loss = debt - assets;
        }
    }

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }

        uint256 wantBalance = want.balanceOf(address(this));
        masterchef.deposit(pid, wantBalance);
    }

    function withdrawFromFarm(uint256 _amountToWithdraw) internal {
        if (bypassWithdrawFee) {
            //Workaround to get rewards even if we withdraw early
            if (pendingReward() > 0 && harvestOnLiq) {
                masterchef.deposit(pid, 0);
            }
            //Withdraw all funds to get max funds
            masterchef.emergencyWithdraw(pid);
        } else {
            masterchef.withdraw(pid, _amountToWithdraw);
        }
    }

    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 totalAssets = want.balanceOf(address(this));
        if (_amountNeeded > totalAssets) {
            uint256 amountToFree = _amountNeeded.sub(totalAssets);

            uint256 deposited = masterchef.userInfo(pid, address(this)).amount;
            if (deposited < amountToFree) {
                amountToFree = deposited;
            }
            if (deposited > 0) {
                withdrawFromFarm(amountToFree);
                uint256 newWantBal = want.balanceOf(address(this));
                if (newWantBal > amountToFree) {
                    //Deposit back excess to farm
                    masterchef.deposit(pid, newWantBal.sub(amountToFree));
                }
            }

            _liquidatedAmount = want.balanceOf(address(this));
        } else {
            _liquidatedAmount = _amountNeeded;
        }
    }

    // NOTE: Can override `tendTrigger` and `harvestTrigger` if necessary

    function prepareMigration(address _newStrategy) internal override {
        liquidatePosition(type(uint256).max); //withdraw all. does not matter if we ask for too much
        _sell();
    }

    function emergencyWithdrawal(uint256 _pid) external onlyGuardians {
        masterchef.emergencyWithdraw(_pid);
    }

    function toggleharvestOnLiq() external onlyGuardians {
        harvestOnLiq = !harvestOnLiq;
    }

    //sell all function
    function _sell() internal {
        uint256 rewardBal = reward.balanceOf(address(this));
        if (rewardBal < 10 wei) {
            return;
        }
        if (!swapRewardViaSecondaryRouter) {
            rewardRouter.swapExactTokensForTokens(
                rewardBal,
                uint256(0),
                getTokenOutPath(address(reward), address(want)),
                address(this),
                now
            );
        } else {
            rewardRouter.swapExactTokensForTokens(
                rewardBal,
                uint256(0),
                getTokenOutPath(address(reward), address(wftm)),
                address(this),
                now
            );
            wantRouter.swapExactTokensForTokens(
                IERC20(wftm).balanceOf(address(this)),
                uint256(0),
                getTokenOutPath(address(wftm), address(want)),
                address(this),
                now
            );
        }
    }

    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {}
}
