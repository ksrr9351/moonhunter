const hre = require("hardhat");

const USDT_ADDRESSES = {
  1: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
  11155111: "0x7169D38820dfd117C3FA1f22a697dBA58d90BA06",
  56: "0x55d398326f99059fF775485246999027B3197955",
  137: "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
  42161: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
};

const ONEINCH_ROUTER = {
  1: "0x111111125421cA6dc452d289314280a0f8842A65",
  11155111: "0x111111125421cA6dc452d289314280a0f8842A65",
  56: "0x111111125421cA6dc452d289314280a0f8842A65",
  137: "0x111111125421cA6dc452d289314280a0f8842A65",
  42161: "0x111111125421cA6dc452d289314280a0f8842A65",
};

async function main() {
  const network = await hre.ethers.provider.getNetwork();
  const chainId = Number(network.chainId);
  console.log(`\nDeploying to chain: ${chainId}`);
  console.log(`Network: ${hre.network.name}`);

  const [deployer] = await hre.ethers.getSigners();
  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log(`Deployer: ${deployer.address}`);
  console.log(`Balance: ${hre.ethers.formatEther(balance)} ETH\n`);

  const treasuryAddress = process.env.TREASURY_ADDRESS || deployer.address;
  const usdtAddress = USDT_ADDRESSES[chainId];
  const routerAddress = ONEINCH_ROUTER[chainId];
  const feePercent = parseInt(process.env.FEE_PERCENT || "200");

  if (!usdtAddress) {
    throw new Error(`USDT address not configured for chain ${chainId}`);
  }
  if (!routerAddress) {
    throw new Error(`1inch router not configured for chain ${chainId}`);
  }

  console.log("Constructor arguments:");
  console.log(`  Treasury:      ${treasuryAddress}`);
  console.log(`  USDT:          ${usdtAddress}`);
  console.log(`  1inch Router:  ${routerAddress}`);
  console.log(`  Fee:           ${feePercent / 100}% (${feePercent} basis points)\n`);

  const FeeProxy = await hre.ethers.getContractFactory("MoonHuntersFeeProxy");
  const proxy = await FeeProxy.deploy(
    treasuryAddress,
    usdtAddress,
    routerAddress,
    feePercent
  );

  await proxy.waitForDeployment();
  const contractAddress = await proxy.getAddress();

  console.log(`MoonHuntersFeeProxy deployed to: ${contractAddress}\n`);

  console.log("--- Update frontend/src/config/contractConfig.js ---");
  console.log(`CONTRACT_ADDRESSES[${chainId}] = "${contractAddress}"`);
  console.log(`TREASURY_ADDRESS = "${treasuryAddress}"\n`);

  console.log("--- Verify on block explorer ---");
  console.log(
    `npx hardhat verify --network ${hre.network.name} ${contractAddress} "${treasuryAddress}" "${usdtAddress}" "${routerAddress}" ${feePercent}\n`
  );
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
