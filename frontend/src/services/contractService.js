import { BrowserProvider, Contract, parseUnits, formatUnits } from "ethers";
import {
  CONTRACT_ADDRESSES,
  FEE_PERCENT,
  FEE_PROXY_ABI,
  ERC20_ABI,
} from "../config/contractConfig";
import { getExplorerUrl as _getChainExplorer, getChainById } from "./chainService";
import apiClient from "./apiClient";

function getProvider() {
  if (!window.ethereum) {
    throw new Error("No wallet provider found. Please install MetaMask or another Web3 wallet.");
  }
  return new BrowserProvider(window.ethereum);
}

export function getContractAddress(chainId) {
  return CONTRACT_ADDRESSES[chainId] || "";
}

export function isContractDeployed(chainId) {
  const addr = getContractAddress(chainId);
  return !!addr && addr !== "" && addr !== "0x0000000000000000000000000000000000000000";
}

export function estimateFee(amount) {
  return (parseFloat(amount) * FEE_PERCENT) / 100;
}

export function getExplorerTxUrl(chainId, txHash) {
  const base = _getChainExplorer(chainId);
  if (!base) return null;
  return `${base}/tx/${txHash}`;
}

async function getSwapDataFromBackend(chainId, srcToken, dstToken, amount, scAddress) {
  const response = await apiClient.post("/api/dex/swap-data-for-sc", {
    chain_id: chainId,
    src_token: srcToken,
    dst_token: dstToken,
    amount: amount,
    sc_address: scAddress,
  });
  return response.data;
}

async function buyViaSC(tokenAddress, usdtAmount, minOutputAmount, chainId) {
  const provider = getProvider();
  const signer = await provider.getSigner();
  const scAddress = getContractAddress(chainId);
  const chainData = getChainById(chainId);
  const usdtAddress = chainData?.usdt_address;

  if (!usdtAddress) {
    throw new Error(`USDT not available for chain ${chainId}`);
  }

  const usdtContract = new Contract(usdtAddress, ERC20_ABI, signer);
  const decimals = await usdtContract.decimals();
  const amountWei = parseUnits(usdtAmount.toString(), decimals);

  const allowance = await usdtContract.allowance(await signer.getAddress(), scAddress);
  if (allowance < amountWei) {
    const approveTx = await usdtContract.approve(scAddress, amountWei);
    await approveTx.wait();
  }

  const swapResult = await getSwapDataFromBackend(
    chainId,
    usdtAddress,
    tokenAddress,
    amountWei.toString(),
    scAddress
  );

  if (!swapResult.success) {
    throw new Error(swapResult.error || "Failed to generate swap data");
  }

  const sc = new Contract(scAddress, FEE_PROXY_ABI, signer);
  const minOutput = parseUnits(minOutputAmount.toString(), 18);
  const tx = await sc.buyToken(tokenAddress, amountWei, minOutput, swapResult.tx.data);
  const receipt = await tx.wait();
  return { tx, receipt };
}

async function buyVia1inch(tokenAddress, usdtAmount, slippage, chainId) {
  const provider = getProvider();
  const signer = await provider.getSigner();
  const userAddress = await signer.getAddress();
  const chainData = getChainById(chainId);
  const usdtAddress = chainData?.usdt_address;

  if (!usdtAddress) {
    throw new Error(`USDT not available for chain ${chainId}`);
  }

  const usdtContract = new Contract(usdtAddress, ERC20_ABI, signer);
  const decimals = await usdtContract.decimals();
  const amountWei = parseUnits(usdtAmount.toString(), decimals);

  const spenderRes = await apiClient.get(`/api/dex/spender?chain_id=${chainId}`);
  if (!spenderRes.data.success) {
    throw new Error("Failed to get 1inch spender address");
  }
  const spenderAddress = spenderRes.data.address;

  const allowance = await usdtContract.allowance(userAddress, spenderAddress);
  if (allowance < amountWei) {
    const approveTx = await usdtContract.approve(spenderAddress, amountWei);
    await approveTx.wait();
  }

  const swapRes = await apiClient.get("/api/dex/swap", {
    params: {
      src_token: usdtAddress,
      dst_token: tokenAddress,
      amount: amountWei.toString(),
      from_address: userAddress,
      slippage: slippage || 1,
      chain_id: chainId,
    },
  });

  if (!swapRes.data.success) {
    throw new Error(swapRes.data.error || "Failed to get swap transaction");
  }

  const txData = swapRes.data.tx;
  const tx = await signer.sendTransaction({
    to: txData.to,
    data: txData.data,
    value: txData.value || "0",
    gasLimit: txData.gas ? BigInt(txData.gas) : undefined,
  });
  const receipt = await tx.wait();
  return { tx, receipt };
}

export async function buyToken(tokenAddress, usdtAmount, minOutputAmount, chainId, slippage) {
  if (isContractDeployed(chainId)) {
    return buyViaSC(tokenAddress, usdtAmount, minOutputAmount, chainId);
  }
  return buyVia1inch(tokenAddress, usdtAmount, slippage, chainId);
}

async function sellViaSC(tokenAddress, tokenAmount, minUsdtOutput, chainId) {
  const provider = getProvider();
  const signer = await provider.getSigner();
  const scAddress = getContractAddress(chainId);
  const chainData = getChainById(chainId);
  const usdtAddress = chainData?.usdt_address;

  const tokenContract = new Contract(tokenAddress, ERC20_ABI, signer);
  const decimals = await tokenContract.decimals();
  const amountWei = parseUnits(tokenAmount.toString(), decimals);

  const allowance = await tokenContract.allowance(await signer.getAddress(), scAddress);
  if (allowance < amountWei) {
    const approveTx = await tokenContract.approve(scAddress, amountWei);
    await approveTx.wait();
  }

  const swapResult = await getSwapDataFromBackend(
    chainId,
    tokenAddress,
    usdtAddress,
    amountWei.toString(),
    scAddress
  );

  if (!swapResult.success) {
    throw new Error(swapResult.error || "Failed to generate swap data");
  }

  const sc = new Contract(scAddress, FEE_PROXY_ABI, signer);
  const usdtContract = new Contract(usdtAddress, ERC20_ABI, signer);
  const usdtDecimals = await usdtContract.decimals();
  const minOutput = parseUnits(minUsdtOutput.toString(), usdtDecimals);
  const tx = await sc.sellToken(tokenAddress, amountWei, minOutput, swapResult.tx.data);
  const receipt = await tx.wait();
  return { tx, receipt };
}

async function sellVia1inch(tokenAddress, tokenAmount, slippage, chainId) {
  const provider = getProvider();
  const signer = await provider.getSigner();
  const userAddress = await signer.getAddress();
  const chainData = getChainById(chainId);
  const usdtAddress = chainData?.usdt_address;

  if (!usdtAddress) {
    throw new Error(`USDT not available for chain ${chainId}`);
  }

  const tokenContract = new Contract(tokenAddress, ERC20_ABI, signer);
  const decimals = await tokenContract.decimals();
  const amountWei = parseUnits(tokenAmount.toString(), decimals);

  const spenderRes = await apiClient.get(`/api/dex/spender?chain_id=${chainId}`);
  if (!spenderRes.data.success) {
    throw new Error("Failed to get 1inch spender address");
  }
  const spenderAddress = spenderRes.data.address;

  const allowance = await tokenContract.allowance(userAddress, spenderAddress);
  if (allowance < amountWei) {
    const approveTx = await tokenContract.approve(spenderAddress, amountWei);
    await approveTx.wait();
  }

  const swapRes = await apiClient.get("/api/dex/swap", {
    params: {
      src_token: tokenAddress,
      dst_token: usdtAddress,
      amount: amountWei.toString(),
      from_address: userAddress,
      slippage: slippage || 1,
      chain_id: chainId,
    },
  });

  if (!swapRes.data.success) {
    throw new Error(swapRes.data.error || "Failed to get swap transaction");
  }

  const txData = swapRes.data.tx;
  const tx = await signer.sendTransaction({
    to: txData.to,
    data: txData.data,
    value: txData.value || "0",
    gasLimit: txData.gas ? BigInt(txData.gas) : undefined,
  });
  const receipt = await tx.wait();
  return { tx, receipt };
}

export async function sellToken(tokenAddress, tokenAmount, minUsdtOutput, chainId, slippage) {
  if (isContractDeployed(chainId)) {
    return sellViaSC(tokenAddress, tokenAmount, minUsdtOutput, chainId);
  }
  return sellVia1inch(tokenAddress, tokenAmount, slippage, chainId);
}

export function listenForBuyEvents(chainId, userAddress, callback) {
  if (!isContractDeployed(chainId)) return null;

  try {
    const provider = getProvider();
    const sc = new Contract(getContractAddress(chainId), FEE_PROXY_ABI, provider);
    const filter = sc.filters.BuyExecuted(userAddress);
    sc.on(filter, (user, token, amountIn, amountOut, fee, event) => {
      callback({
        type: "buy",
        user,
        token,
        amountIn: formatUnits(amountIn, 6),
        amountOut: formatUnits(amountOut, 18),
        fee: formatUnits(fee, 6),
        txHash: event.log.transactionHash,
      });
    });
    return () => sc.removeAllListeners(filter);
  } catch {
    return null;
  }
}

export function listenForSellEvents(chainId, userAddress, callback) {
  if (!isContractDeployed(chainId)) return null;

  try {
    const provider = getProvider();
    const sc = new Contract(getContractAddress(chainId), FEE_PROXY_ABI, provider);
    const filter = sc.filters.SellExecuted(userAddress);
    sc.on(filter, (user, token, amountIn, amountOut, fee, event) => {
      callback({
        type: "sell",
        user,
        token,
        amountIn: formatUnits(amountIn, 18),
        amountOut: formatUnits(amountOut, 6),
        fee: formatUnits(fee, 6),
        txHash: event.log.transactionHash,
      });
    });
    return () => sc.removeAllListeners(filter);
  } catch {
    return null;
  }
}
