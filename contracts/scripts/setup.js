const hre = require("hardhat");

const TOP_TOKENS = {
  1: [
    { symbol: "WETH", address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" },
    { symbol: "WBTC", address: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599" },
    { symbol: "LINK", address: "0x514910771AF9Ca656af840dff83E8264EcF986CA" },
    { symbol: "UNI", address: "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984" },
    { symbol: "AAVE", address: "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9" },
    { symbol: "MKR", address: "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2" },
  ],
  56: [
    { symbol: "WBNB", address: "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c" },
    { symbol: "CAKE", address: "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82" },
    { symbol: "XVS", address: "0xcF6BB5389c92Bdda8a3747Ddb454cB7a64626C63" },
  ],
  137: [
    { symbol: "WMATIC", address: "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270" },
    { symbol: "AAVE", address: "0xD6DF932A45C0f255f85145f286eA0b292B21C90B" },
    { symbol: "LINK", address: "0x53E0bca35eC356BD5ddDFebbD1Fc0fD03FaBad39" },
  ],
  42161: [
    { symbol: "WETH", address: "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1" },
    { symbol: "ARB", address: "0x912CE59144191C1204E64559FE8253a0e49E6548" },
    { symbol: "GMX", address: "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a" },
  ],
  11155111: [
    { symbol: "WETH", address: "0x7b79995e5f793A07Bc00c21412e50Ecae098E7f9" },
    { symbol: "USDT", address: "0x7169D38820dfd117C3FA1f22a697dBA58d90BA06" },
    { symbol: "LINK", address: "0x779877A7B0D9E8603169DdbD7836e478b4624789" },
    { symbol: "UNI", address: "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984" },
  ],
};

async function main() {
  const network = await hre.ethers.provider.getNetwork();
  const chainId = Number(network.chainId);

  const contractAddress = process.env.CONTRACT_ADDRESS;
  if (!contractAddress) {
    throw new Error("Set CONTRACT_ADDRESS env var to the deployed proxy address");
  }

  console.log(`Setting up MoonHuntersFeeProxy at ${contractAddress} on chain ${chainId}\n`);

  const FeeProxy = await hre.ethers.getContractFactory("MoonHuntersFeeProxy");
  const proxy = FeeProxy.attach(contractAddress);

  const currentFee = await proxy.feePercent();
  console.log(`Current fee: ${Number(currentFee) / 100}%`);

  const tokens = TOP_TOKENS[chainId] || [];
  if (tokens.length === 0) {
    console.log("No tokens configured for this chain. Add manually.");
    return;
  }

  console.log(`\nWhitelisting ${tokens.length} tokens...\n`);

  for (const token of tokens) {
    const isAlready = await proxy.isWhitelisted(token.address);
    if (isAlready) {
      console.log(`  [SKIP] ${token.symbol} (${token.address}) — already whitelisted`);
      continue;
    }

    const tx = await proxy.addWhitelistedToken(token.address);
    await tx.wait();
    console.log(`  [OK]   ${token.symbol} (${token.address}) — whitelisted`);
  }

  console.log("\nSetup complete!");
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
