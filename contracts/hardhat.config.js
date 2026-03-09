require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const DEPLOYER_PRIVATE_KEY = process.env.DEPLOYER_PRIVATE_KEY || "0x" + "0".repeat(64);

module.exports = {
  paths: {
    sources: "./src",
    cache: "./cache",
    artifacts: "./artifacts",
  },
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },
  networks: {
    hardhat: {},
    sepolia: {
      url: process.env.RPC_URL_SEPOLIA || "https://ethereum-sepolia-rpc.publicnode.com",
      accounts: [DEPLOYER_PRIVATE_KEY],
      chainId: 11155111,
      timeout: 120000,
    },
    ethereum: {
      url: process.env.RPC_URL_ETH || "https://ethereum.publicnode.com",
      accounts: [DEPLOYER_PRIVATE_KEY],
      chainId: 1,
    },
    polygon: {
      url: process.env.RPC_URL_POLYGON || "https://polygon-rpc.com",
      accounts: [DEPLOYER_PRIVATE_KEY],
      chainId: 137,
    },
    arbitrum: {
      url: process.env.RPC_URL_ARBITRUM || "https://arb1.arbitrum.io/rpc",
      accounts: [DEPLOYER_PRIVATE_KEY],
      chainId: 42161,
    },
    bsc: {
      url: process.env.RPC_URL_BSC || "https://bsc-dataseed.binance.org",
      accounts: [DEPLOYER_PRIVATE_KEY],
      chainId: 56,
    },
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY || "",
  },
};
