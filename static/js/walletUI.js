
    // Initialize web3
let web3;

async function initWeb3() {
  if (window.ethereum) {
    web3 = new Web3(window.ethereum);
    try {
      // Request account access
      await window.ethereum.enable();
    } catch (error) {
      console.error(error);
    }
  } else {
    alert('Please install MetaMask!');
    return;
  }
}

initWeb3();

let account;
let contract1;
let contract2;

// Conectar a la red
document.getElementById('connectButton').addEventListener('click', async () => {
  if (!web3) {
    alert('Please connect wallet!');
    return;
  }
  
  if (typeof window.ethereum !== 'undefined') {
    const chainId = '0x13881'; // Reemplaza esto con el ID de cadena de tu red
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId }],  
      });
        
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      account = accounts[0];
    } catch (error) {
      console.error(error);
    }
  } else {
    alert('Please install MetaMask!');
  }
});

// Crear nueva carta 
document.getElementById('createNewDocButton').addEventListener('click', async () => {
  if (!web3) {
    alert('Please connect wallet!');
    return;
  }

  const contractAddress = '0x90C40DA8A3D793bF48d8D635A54c8BFD7C6AC0B2';
  const abi = `[
    {
        "constant": true,
        "inputs": [],
        "name": "documentPrice",
        "outputs": [
            {
                "name": "",
                "type": "uint256"
            }
        ],
        "payable": false,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {
                "name": "_documentPrice",
                "type": "uint256"
            }
        ],
        "name": "setDocumentPrice",
        "outputs": [],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {
                "name": "_amountBurn",
                "type": "uint256"
            }
        ],
        "name": "BurnTokens",
        "outputs": [],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {
                "name": "_quantity_docs",
                "type": "uint256"
            }
        ],
        "name": "create_docs",
        "outputs": [],
        "payable": false,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "_getDocsCreated",
        "outputs": [
            {
                "_name":"",
                "_type":"uint256"
            }
         ],
         "_payable":"false",
         "_stateMutability":"view",
         "_type":"function"
     },
     {
         "_constant":"false",
         "_inputs":[
             {
                 "_name":"_holder",
                 "_type":"address"
             }
         ],
         "_name":"resetDocsCreated",
         "_outputs":[],
         "_payable":"false",
         "_stateMutability":"nonpayable",
         "_type":"function"
     }
]`;
  
  contract1 = new web3.eth.Contract(JSON.parse(abi), contractAddress);

  const quantityDocs = 1; 
  try {
    await contract1.methods.create_docs(quantityDocs).send({ from: account });
  } catch (error) {
    console.error(error);
  }
});


// Comprar token  
document.getElementById('buyTokenButton').addEventListener('click', async () => {
  if (!web3) {
    alert('Please connect wallet!');
    return;
  }

const abiIco = `[
  {
    "constant": false, 
    "inputs": [
      {
        "name": "_amount",
        "type": "uint256"
      }
    ],
    "name": "depositToken",
    "outputs": [],
    "payable": false,
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "constant": false,
    "inputs": [
      {
        "name": "_numberOfTokens",
        "type": "uint256"
      }
    ],
    "name": "buyTokens",
    "outputs": [],
    "payable": true,
    "stateMutability": "payable",
    "type": "function"
  },
  {
    "constant": true,
    "inputs": [
      {
        "name": "_numberOfTokens",
        "type": "uint256"
      }
    ],
    "name": "calculatePrice",
    "outputs": [
      {
        "name": "",
        "type": "uint256"
      }
    ],
    "payable": false,
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": true, 
    "inputs": [],
    "name": "getRemainingTokens",
    "outputs": [
      {
        "name": "",
        "type": "uint256"
      }
    ],
    "payable": false, 
    "stateMutability": "view",
    "type": "function"
  },
  {
    "constant": false,
    "inputs": [],
    "name": "returnRemainingTokens",
    "outputs": [],
    "payable": false,
    "stateMutability": "nonpayable",
    "type": "function"
  },
  {
    "constant": false,
    "inputs": [],
    "name": "withdraw",
    "outputs": [],
    "payable": false,
    "stateMutability": "nonpayable",
    "type": "function"
  }
]`;
  const contractAddress = '0x5bf6390aA7a8D377920ff91A98CD611801D86400';
  
  contract2 = new web3.eth.Contract(JSON.parse(abiIco), contractAddress);
    
  const _numberOfTokens = parseInt(document.getElementById('tokenNumber').value);


  try {
    const priceInWei = await contract2.methods.calculatePrice(_numberOfTokens).call();  
    
    await contract2.methods.buyTokens(_numberOfTokens).send({ from: account, value: priceInWei });
  } catch (error) {    
    console.error(error);
  }
});
