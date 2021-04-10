// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

interface ChefLike {
    struct UserInfo {
        uint256 amount; // How many LP tokens the user has provided.
        uint256 rewardDebt; // Reward debt.
    }

    struct PoolInfo {
        address stakingToken; // Address of staking token contract.
        uint256 allocPoint; // How many allocation points assigned to this pool.
        uint256 lastRewardBlock; // Last block number that distribution occurs.
        uint256 accRewardPerShare; // Accumulated reward tokens per share, times 1e24. See below.
        uint16 earlyWithdrawalFeeBP; // Early withdrawal fee in basis points
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

    function pendingReward(uint256 _pid, address _user)
        external
        view
        returns (uint256);
}

// These are the core Yearn libraries
import "@yearnvaults/contracts/BaseStrategy.sol";
import {
    SafeERC20,
    SafeMath,
    IERC20,
    Address
} from "@openzeppelin/contracts/token/ERC20/SafeERC20.sol";
import "@openzeppelin/contracts/math/Math.sol";

import "./Interfaces/UniswapInterfaces/IUniswapV2Router02.sol";

contract Strategy is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;

    ChefLike public masterchef;
    IERC20 public reward;

    address private constant uniswapRouter =
        address(0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D);
    address private constant sushiswapRouter =
        address(0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F);
    address private constant weth =
        address(0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2);

    IUniswapV2Router02 public router;

    uint256 public pid;

    address[] public path;

    bool public harvestOnLiq;

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
        uint256 _pid
    ) public BaseStrategy(_vault) {
        _initializeStrat(_masterchef, _reward, _router, _pid);
    }

    function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _masterchef,
        address _reward,
        address _router,
        uint256 _pid
    ) external {
        //note: initialise can only be called once. in _initialize in BaseStrategy we have: require(address(want) == address(0), "Strategy already initialized");
        _initialize(_vault, _strategist, _rewards, _keeper);
        _initializeStrat(_masterchef, _reward, _router, _pid);
    }

    function _initializeStrat(
        address _masterchef,
        address _reward,
        address _router,
        uint256 _pid
    ) internal {
        require(
            address(router) == address(0),
            "Masterchef Strategy already initialized"
        );
        require(
            _router == uniswapRouter || _router == sushiswapRouter,
            "incorrect router"
        );

        // You can set these parameters on deployment to whatever you want
        maxReportDelay = 6300;
        profitFactor = 1500;
        debtThreshold = 1_000_000 * 1e18;
        masterchef = ChefLike(_masterchef);
        reward = IERC20(_reward);
        router = IUniswapV2Router02(_router);
        pid = _pid;
        path = getTokenOutPath(_reward, address(want));
        harvestOnLiq = true;
        require(
            address(want) == masterchef.poolInfo(pid).stakingToken,
            "wrong pid"
        );

        want.safeApprove(_masterchef, type(uint256).max);
        reward.safeApprove(_router, type(uint256).max);
    }

    function cloneStrategy(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        address _masterchef,
        address _reward,
        address _router,
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

        Strategy(newStrategy).initialize(
            _vault,
            _strategist,
            _rewards,
            _keeper,
            _masterchef,
            _reward,
            _router,
            _pid
        );

        emit Cloned(newStrategy);
    }

    function setRouter(address _router) public onlyAuthorized {
        require(
            _router == uniswapRouter || _router == sushiswapRouter,
            "incorrect router"
        );
        router = IUniswapV2Router02(_router);
        reward.safeApprove(_router, 0);
        reward.safeApprove(_router, type(uint256).max);
    }

    function getTokenOutPath(address _token_in, address _token_out)
        internal
        view
        returns (address[] memory _path)
    {
        bool is_weth =
            _token_in == address(weth) || _token_out == address(weth);
        _path = new address[](is_weth ? 2 : 3);
        _path[0] = _token_in;
        if (is_weth) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(weth);
            _path[2] = _token_out;
        }
    }

    function setPath(address[] calldata _path) public onlyGuardians {
        path = _path;
    }

    // ******** OVERRIDE THESE METHODS FROM BASE CONTRACT ************

    function name() external view override returns (string memory) {
        return "StrategyMasterchefGenericMod";
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        uint256 deposited = masterchef.userInfo(pid, address(this)).amount;
        return want.balanceOf(address(this)).add(deposited);
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
        if (masterchef.pendingReward(pid, address(this)) > 0)
            masterchef.deposit(pid, 0);

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
                //Workaround to get rewards even if we withdraw early
                if (
                    masterchef.pendingReward(pid, address(this)) > 0 &&
                    harvestOnLiq
                ) {
                    masterchef.deposit(pid, 0);
                }
                //Withdraw all funds to get max funds
                masterchef.emergencyWithdraw(pid);
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

    function emergencyWithdrawal(uint256 _pid) external onlyGovernance {
        masterchef.emergencyWithdraw(_pid);
    }

    function toggleharvestOnLiq() external onlyGuardians {
        harvestOnLiq = !harvestOnLiq;
    }

    //sell all function
    function _sell() internal {
        uint256 rewardBal = reward.balanceOf(address(this));
        if (rewardBal == 0) {
            return;
        }
        if (path.length == 0) {
            router.swapExactTokensForTokens(
                rewardBal,
                uint256(0),
                getTokenOutPath(address(reward), address(want)),
                address(this),
                now
            );
        } else {
            router.swapExactTokensForTokens(
                rewardBal,
                uint256(0),
                path,
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
