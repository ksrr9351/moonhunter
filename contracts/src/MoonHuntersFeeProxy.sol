// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract MoonHuntersFeeProxy is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    uint256 public constant MAX_FEE = 500;
    uint256 public constant FEE_DENOMINATOR = 10000;

    address public treasury;
    address public immutable usdt;
    address public immutable oneInchRouter;
    uint256 public feePercent;
    bool public paused;

    mapping(address => bool) private _whitelistedTokens;
    mapping(address => uint256) public accumulatedFees;
    mapping(bytes4 => bool) private _allowedSelectors;

    event BuyExecuted(
        address indexed user,
        address indexed token,
        uint256 amountIn,
        uint256 amountOut,
        uint256 fee
    );

    event SellExecuted(
        address indexed user,
        address indexed token,
        uint256 amountIn,
        uint256 amountOut,
        uint256 fee
    );

    event FeeCollected(address indexed token, uint256 amount);
    event FeeUpdated(uint256 oldFee, uint256 newFee);
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    event Paused(address indexed by);
    event Unpaused(address indexed by);

    modifier whenNotPaused() {
        require(!paused, "Contract is paused");
        _;
    }

    modifier onlyWhitelisted(address token) {
        require(_whitelistedTokens[token], "Token not whitelisted");
        _;
    }

    constructor(
        address _treasury,
        address _usdtAddress,
        address _oneInchRouter,
        uint256 _feePercent
    ) Ownable(msg.sender) {
        require(_treasury != address(0), "Invalid treasury");
        require(_usdtAddress != address(0), "Invalid USDT address");
        require(_oneInchRouter != address(0), "Invalid 1inch router");
        require(_feePercent <= MAX_FEE, "Fee exceeds maximum");

        treasury = _treasury;
        usdt = _usdtAddress;
        oneInchRouter = _oneInchRouter;
        feePercent = _feePercent;

        _allowedSelectors[0x12aa3caf] = true; // swap
        _allowedSelectors[0xe2c95c82] = true; // unoswapTo
        _allowedSelectors[0xbc80f1a8] = true; // uniswapV3SwapTo
        _allowedSelectors[0x093d4fa5] = true; // clipperSwapTo
        _allowedSelectors[0xe5d7bde6] = true; // fillOrderTo
    }

    function buyToken(
        address token,
        uint256 usdtAmount,
        uint256 minOutput,
        bytes calldata swapData
    ) external nonReentrant whenNotPaused onlyWhitelisted(token) {
        require(usdtAmount > 0, "Amount must be > 0");

        IERC20(usdt).safeTransferFrom(msg.sender, address(this), usdtAmount);

        uint256 fee = (usdtAmount * feePercent) / FEE_DENOMINATOR;
        uint256 swapAmount = usdtAmount - fee;

        if (fee > 0) {
            accumulatedFees[usdt] += fee;
            emit FeeCollected(usdt, fee);
        }

        _validateSwapData(swapData);

        IERC20(usdt).safeIncreaseAllowance(oneInchRouter, swapAmount);

        uint256 tokenBalanceBefore = IERC20(token).balanceOf(address(this));

        (bool success, ) = oneInchRouter.call(swapData);
        require(success, "1inch swap failed");

        _resetAllowance(usdt);

        uint256 tokenBalanceAfter = IERC20(token).balanceOf(address(this));
        uint256 tokensReceived = tokenBalanceAfter - tokenBalanceBefore;
        require(tokensReceived >= minOutput, "Slippage too high");

        IERC20(token).safeTransfer(msg.sender, tokensReceived);

        emit BuyExecuted(msg.sender, token, usdtAmount, tokensReceived, fee);
    }

    function sellToken(
        address token,
        uint256 tokenAmount,
        uint256 minUsdtOutput,
        bytes calldata swapData
    ) external nonReentrant whenNotPaused onlyWhitelisted(token) {
        require(tokenAmount > 0, "Amount must be > 0");

        IERC20(token).safeTransferFrom(msg.sender, address(this), tokenAmount);

        _validateSwapData(swapData);

        IERC20(token).safeIncreaseAllowance(oneInchRouter, tokenAmount);

        uint256 usdtBalanceBefore = IERC20(usdt).balanceOf(address(this));

        (bool success, ) = oneInchRouter.call(swapData);
        require(success, "1inch swap failed");

        _resetAllowance(token);

        uint256 usdtBalanceAfter = IERC20(usdt).balanceOf(address(this));
        uint256 usdtReceived = usdtBalanceAfter - usdtBalanceBefore;

        uint256 fee = (usdtReceived * feePercent) / FEE_DENOMINATOR;
        uint256 userAmount = usdtReceived - fee;
        require(userAmount >= minUsdtOutput, "Slippage too high");

        if (fee > 0) {
            accumulatedFees[usdt] += fee;
            emit FeeCollected(usdt, fee);
        }

        IERC20(usdt).safeTransfer(msg.sender, userAmount);

        emit SellExecuted(msg.sender, token, tokenAmount, userAmount, fee);
    }

    function setFeePercent(uint256 fee) external onlyOwner {
        require(fee <= MAX_FEE, "Fee exceeds maximum (5%)");
        uint256 oldFee = feePercent;
        feePercent = fee;
        emit FeeUpdated(oldFee, fee);
    }

    function withdrawFees() external onlyOwner {
        uint256 usdtFees = accumulatedFees[usdt];
        require(usdtFees > 0, "No fees to withdraw");

        accumulatedFees[usdt] = 0;
        IERC20(usdt).safeTransfer(treasury, usdtFees);
    }

    function pause() external onlyOwner {
        paused = true;
        emit Paused(msg.sender);
    }

    function unpause() external onlyOwner {
        paused = false;
        emit Unpaused(msg.sender);
    }

    function recoverTokens(address token, uint256 amount) external onlyOwner {
        require(amount > 0, "Amount must be > 0");
        IERC20(token).safeTransfer(treasury, amount);
    }

    function addWhitelistedToken(address token) external onlyOwner {
        require(token != address(0), "Invalid token address");
        _whitelistedTokens[token] = true;
    }

    function removeWhitelistedToken(address token) external onlyOwner {
        _whitelistedTokens[token] = false;
    }

    function isWhitelisted(address token) external view returns (bool) {
        return _whitelistedTokens[token];
    }

    function setTreasury(address _newTreasury) external onlyOwner {
        require(_newTreasury != address(0), "Invalid treasury address");
        address oldTreasury = treasury;
        treasury = _newTreasury;
        emit TreasuryUpdated(oldTreasury, _newTreasury);
    }

    function addAllowedSelector(bytes4 selector) external onlyOwner {
        _allowedSelectors[selector] = true;
    }

    function removeAllowedSelector(bytes4 selector) external onlyOwner {
        _allowedSelectors[selector] = false;
    }

    function isSelectorAllowed(bytes4 selector) external view returns (bool) {
        return _allowedSelectors[selector];
    }

    function _validateSwapData(bytes calldata swapData) internal view {
        require(swapData.length >= 4, "SwapData too short");
        bytes4 selector = bytes4(swapData[:4]);
        require(_allowedSelectors[selector], "Swap function not allowed");
    }

    function _resetAllowance(address token) internal {
        uint256 remaining = IERC20(token).allowance(address(this), oneInchRouter);
        if (remaining > 0) {
            IERC20(token).forceApprove(oneInchRouter, 0);
        }
    }
}
