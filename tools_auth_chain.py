import asyncio
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solders.signature import Signature
from solders.pubkey import Pubkey
import json

# Convert UiTransactionTokenBalance to dict
def token_balance_to_dict(balance):
    def safe_convert(obj):
        # Convert Pubkey to string, otherwise leave the object intact
        return str(obj) if isinstance(obj, Pubkey) else obj

    return {
        "account_index": balance.account_index,
        "mint": safe_convert(balance.mint),
        "ui_token_amount": {
            "ui_amount": balance.ui_token_amount.ui_amount,
            "decimals": balance.ui_token_amount.decimals,
            "amount": balance.ui_token_amount.amount,
            "ui_amount_string": balance.ui_token_amount.ui_amount_string,
        },
        "owner": safe_convert(balance.owner),
        "program_id": safe_convert(balance.program_id),
    }

# Helper function to safely get ui_amount
def get_ui_amount(token_amount):
    if token_amount.ui_amount is not None:
        return token_amount.ui_amount
    else:
        calculated_amount = float(token_amount.amount) / (10 ** token_amount.decimals)
        print(f"[DEBUG] Calculated ui_amount: {calculated_amount} from amount: {token_amount.amount} and decimals: {token_amount.decimals}")
        return calculated_amount

async def get_transaction_data(tx_signature_str: str):
    async with AsyncClient("https://boldest-orbital-surf.solana-mainnet.quiknode.pro/bac5b8883f3f8d33308063dfb0f83fb70bddad1d") as solana_client:
        try:
            tx_signature = Signature.from_string(tx_signature_str)
            print(f"[DEBUG] Fetching transaction data for signature: {tx_signature_str}")

            transaction_response = await solana_client.get_transaction(
                tx_signature,
                commitment=Confirmed,
                max_supported_transaction_version=0,
            )

            print(f"[DEBUG] Transaction response: {transaction_response}")

            if transaction_response and transaction_response.value:
                tx = transaction_response.value

                if hasattr(tx, "transaction") and hasattr(tx.transaction, "meta"):
                    meta = tx.transaction.meta
                    if meta and meta.pre_token_balances and meta.post_token_balances:
                        print("[DEBUG] Successfully retrieved pre and post token balances.")
                        return meta.pre_token_balances, meta.post_token_balances
                    else:
                        print("[ERROR] Meta data does not contain pre_token_balances or post_token_balances.")
                else:
                    print("[ERROR] Transaction data does not have 'transaction' or 'meta' attributes.")
            else:
                print("[ERROR] Transaction response is None or does not contain 'value'.")

            raise ValueError("No valid transaction data found.")

        except Exception as e:
            print(f"[ERROR] An error occurred while fetching transaction data: {e}")
            return None, None

def request_data_chain(tx_signature):
    async def process_tx_signature():
        pre_balances, post_balances = await get_transaction_data(tx_signature)
        return pre_balances, post_balances

    try:
        return asyncio.run(process_tx_signature())
    except Exception as e:
        print(f"[ERROR] Asyncio run failed: {e}")
        return None, None

def auth_sol_wallet(wallet_for_auth, amount_send, wallet_recipient, tokens_available, tx_signature):
    amount_send= float(amount_send)
    print(f"[INFO] Authenticating transaction.\n"
          f"Wallet For Auth: {wallet_for_auth}\n"
          f"Amount Send: {amount_send}\n"
          f"Wallet Recipient: {wallet_recipient}\n"
          f"Tokens Available: {tokens_available}\n"
          f"Signature: {tx_signature}")

    pre_balances, post_balances = request_data_chain(tx_signature)

    if pre_balances is None or post_balances is None:
        print("[ERROR] No valid response from transaction data.")
        return {"error": "No valid response from transaction data."}

    print("[DEBUG] Pre-transaction token balances:")
    for balance in pre_balances:
        print(json.dumps(token_balance_to_dict(balance), indent=4))

    print("\n[DEBUG] Post-transaction token balances:")
    for balance in post_balances:
        print(json.dumps(token_balance_to_dict(balance), indent=4))

    sender_wallet = None
    token_address = None
    recipient_amount = 0.0
    actual_recipient_wallet = None

    # Iterar sobre los balances para identificar al emisor y receptor
    for pre_balance in pre_balances:
        post_balance = next((b for b in post_balances if b.account_index == pre_balance.account_index), None)
        if post_balance:
            pre_ui_amount = get_ui_amount(pre_balance.ui_token_amount)
            post_ui_amount = get_ui_amount(post_balance.ui_token_amount)
            amount_change = round(post_ui_amount - pre_ui_amount, 6)
            print(f"[DEBUG] Account Index: {pre_balance.account_index}, "
                  f"Pre UI Amount: {pre_ui_amount}, "
                  f"Post UI Amount: {post_ui_amount}, "
                  f"Amount Change: {amount_change}")

            if amount_change < 0 and not sender_wallet:
                sender_wallet = post_balance.owner
                token_address = str(post_balance.mint)
                print(f"[INFO] Identified sender wallet: {sender_wallet} with token: {token_address}")
            elif amount_change > 0:
                recipient_amount += amount_change
                actual_recipient_wallet = post_balance.owner
                print(f"[INFO] Identified recipient wallet: {actual_recipient_wallet} with amount: {amount_change}")

    # Verificar si el receptor es el esperado y la cantidad es correcta
    if actual_recipient_wallet is None:
        print("[ERROR] No recipient wallet found in transaction data.")
        return {"error": "No recipient wallet found in transaction."}

    # Comparar la cantidad enviada con la cantidad esperada dentro de una tolerancia
    tolerance = 0.8  # Tolerancia de 0.001
    if abs(amount_send - recipient_amount) > tolerance:
        error_msg = f"Error: La cantidad enviada ({recipient_amount}) no coincide con la cantidad esperada ({amount_send})."
        print(f"[ERROR] {error_msg}")
        return {"error": error_msg}

    # Verificar que la wallet del destinatario coincide con la esperada
    if str(wallet_recipient) != str(actual_recipient_wallet):
        error_msg = f"Error: La wallet destinataria esperada ({wallet_recipient}) no coincide con la encontrada ({actual_recipient_wallet})."
        print(f"[ERROR] {error_msg}")
        return {"error": error_msg}

    # Verificar que la wallet del emisor coincide con la esperada
    if str(wallet_for_auth) != str(sender_wallet):
        error_msg = f"Error: La wallet emisora esperada ({wallet_for_auth}) no coincide con la encontrada ({sender_wallet})."
        print(f"[ERROR] {error_msg}")
        return {"error": error_msg}

    # Verificar que el token es uno de los permitidos
    if token_address and token_address.strip() not in [token.strip() for token in tokens_available]:
        print(f"[ERROR] Identified token address: {token_address}, which is not in available tokens: {tokens_available}")
        return {
            "error": "El token enviado es incorrecto. Solo puedes recargar tu saldo usando tokens específicos."
        }

    print("[INFO] Wallet authenticated successfully.")
    return wallet_for_auth, token_address, recipient_amount
    

def deposit_auth(signature_tx):
    print(f"[INFO] Processing deposit authentication for signature: {signature_tx}")
    pre_balances, post_balances = request_data_chain(signature_tx)

    if pre_balances is None or post_balances is None:
        print("[ERROR] No valid response from transaction data.")
        return {"error": "No valid response from transaction data."}

    token_address = None
    amount_send = None
    sender_wallet = None
    actual_recipient_wallet = None

    # Iterar sobre los balances para identificar al emisor y receptor tolerance
    for pre_balance in pre_balances:
        post_balance = next((b for b in post_balances if b.account_index == pre_balance.account_index), None)
        if post_balance:
            pre_ui_amount = get_ui_amount(pre_balance.ui_token_amount)
            post_ui_amount = get_ui_amount(post_balance.ui_token_amount)
            amount_change = round(post_ui_amount - pre_ui_amount, 6)
            print(f"[DEBUG] Account Index: {pre_balance.account_index}, "
                  f"Pre UI Amount: {pre_ui_amount}, "
                  f"Post UI Amount: {post_ui_amount}, "
                  f"Amount Change: {amount_change}")

            if amount_change < 0 and not sender_wallet:
                sender_wallet = post_balance.owner
                token_address = str(post_balance.mint)
                amount_send = -amount_change
                print(f"[INFO] Identified sender wallet: {sender_wallet} with token: {token_address} and amount_send: {amount_send}")
            elif amount_change > 0:
                actual_recipient_wallet = post_balance.owner
                print(f"[INFO] Identified recipient wallet: {actual_recipient_wallet} with amount: {amount_change}")

    # Verificar que se haya identificado al emisor y al receptor
    if sender_wallet is None or actual_recipient_wallet is None or token_address is None or amount_send is None:
        print("[ERROR] Transaction data is incomplete or incorrect.")
        return {"error": "Transaction data is incomplete or incorrect."}

    print(f"[DEBUG] sender_wallet: {sender_wallet}, "
          f"recipient_wallet: {actual_recipient_wallet}, "
          f"token_address: {token_address}, "
          f"amount_send: {amount_send}")

    return {
        "token_address": token_address,
        "recipient_wallet": actual_recipient_wallet,
        "amount_send": amount_send,
        "sender_wallet": sender_wallet
    }

