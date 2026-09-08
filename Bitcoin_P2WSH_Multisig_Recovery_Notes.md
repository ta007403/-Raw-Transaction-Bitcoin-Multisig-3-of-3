# Bitcoin P2WSH Multisig Recovery Notes

## Purpose

This document records how I recovered Bitcoin from a P2WSH multisig
wallet when I still had the BIP39 seed/passphrase information but needed
to manually derive the private keys and sign a raw Bitcoin transaction.

The process uses two Python scripts:

1.  **Seed → Private Keys**
2.  **Private Keys → Signed Raw Transaction**

> ⚠️ **SECURITY WARNING**
>
> Never put a real BIP39 mnemonic, passphrase, or private key into an
> online website, AI chat, random recovery tool, or untrusted computer.
>
> Ideally perform recovery on an offline computer.
>
> Anyone who obtains the required private keys can spend the Bitcoin.

------------------------------------------------------------------------

# Part 1 --- From Seed Phrase to Private Key

Bitcoin wallets normally do not directly use the BIP39 words as a
Bitcoin private key.

The process looks approximately like this:

``` text
BIP39 mnemonic
      +
BIP39 passphrase
      |
      v
PBKDF2-HMAC-SHA512
      |
      v
512-bit BIP39 seed
      |
      v
BIP32 HD wallet
      |
      +----------------------+
      |                      |
      v                      v
BIP84                    BIP86
m/84'/0'/0'/0/0          m/86'/0'/0'/0/0
      |                      |
      v                      v
Private key              Private key
      |                      |
      v                      v
Public key               Public key
```

## BIP39 Passphrase Matters

The passphrase is part of wallet generation. Changing even one character
creates a completely different wallet.

An empty passphrase:

``` python
passphrase = ""
```

also represents a specific wallet.

Therefore, recovering the mnemonic but using the wrong passphrase will
derive valid keys --- but they will belong to the wrong wallet.

## BIP84

BIP84 is normally associated with native SegWit. A common first
receiving-key derivation is:

``` text
m/84'/0'/0'/0/0
```

Breaking it down:

``` text
m
└── 84'     purpose = BIP84
    └── 0'  coin = Bitcoin mainnet
        └── 0'  account 0
            └── 0   external/receiving chain
                └── 0   address index 0
```

Changing the final index gives another key:

``` text
m/84'/0'/0'/0/0
m/84'/0'/0'/0/1
m/84'/0'/0'/0/2
...
```

The change branch normally uses `m/84'/0'/0'/1/0`.

## BIP86

BIP86 defines key derivation conventions for Taproot wallets. For
example:

``` text
m/86'/0'/0'/0/0
```

The important lesson is that the same mnemonic can generate a huge tree
of different private keys. Knowing the seed is therefore not enough when
manually recovering a wallet; the **derivation path** matters too.

------------------------------------------------------------------------

# Part 2 --- Understanding the UTXO

The Bitcoin I wanted to spend existed as:

``` text
TXID:vout
```

For this recovery:

``` text
3fbf035614e0211e3e76c7f16fbdcb2f841c685c68d6322483de868008de60cf:1
```

The `:1` means `vout = 1`, the second output because output numbering
starts at zero.

That output contained:

``` text
Amount:
12,596,997 sat
= 0.12596997 BTC
```

and:

``` text
scriptPubKey:
00205cf170ca5a4d3be76d576317f3ede85ea4cdba30798484927dab6ea442877132
```

## Recognizing P2WSH

The script begins with:

``` text
00 20
```

where `00` is SegWit version 0 and `20` means push 32 bytes.

For P2WSH:

``` text
scriptPubKey = OP_0 <SHA256(witnessScript)>
```

Therefore:

``` text
SHA256(witnessScript)
=
5cf170ca5a4d3be76d576317f3ede85ea4cdba30798484927dab6ea442877132
```

This is one of the most important safety checks during recovery.

------------------------------------------------------------------------

# Part 3 --- Reconstructing the Multisig Script

For a standard 3-of-3 multisig, the witnessScript conceptually looks
like:

``` text
3
<PUBKEY1>
<PUBKEY2>
<PUBKEY3>
3
CHECKMULTISIG
```

Serialized:

``` text
53
21 <33-byte compressed public key 1>
21 <33-byte compressed public key 2>
21 <33-byte compressed public key 3>
53
ae
```

Where:

``` text
53 = OP_3
21 = push 33 bytes
ae = OP_CHECKMULTISIG
```

The Python recovery script converts each private key into its
corresponding compressed public key and reconstructs the witnessScript.

## Critical Verification

Before signing anything:

``` text
SHA256(witnessScript)
```

MUST equal the hash stored in the UTXO.

``` text
Private keys
     |
     v
Public keys
     |
     v
3-of-3 witnessScript
     |
     v
SHA256
     |
     || MUST MATCH
     v
UTXO P2WSH scriptPubKey
```

If they do not match: **STOP.**

Possible causes include:

-   wrong seed
-   wrong BIP39 passphrase
-   wrong derivation path
-   wrong address index
-   wrong private key
-   wrong public-key ordering
-   `sortedmulti()` was originally used
-   wrong UTXO
-   wrong multisig policy

------------------------------------------------------------------------

# Part 4 --- Previous Output Amount

For SegWit v0 signing, the amount of the UTXO being spent matters.

In the previous raw transaction it was encoded:

``` text
0537c00000000000
```

Bitcoin transaction amounts are unsigned 64-bit **little-endian**
integers.

Python can decode it:

``` python
amount_hex = "0537c00000000000"
amount_sat = int.from_bytes(bytes.fromhex(amount_hex), "little")
print(amount_sat)
```

Result:

``` text
12,596,997 sat
0.12596997 BTC
```

A crucial lesson:

> The previous-output amount is the value of the UTXO being consumed,
> not necessarily the amount being sent by the new transaction.

------------------------------------------------------------------------

# Part 5 --- Input, Output and Miner Fee

The recovery transaction consumed:

``` text
INPUT  = 12,596,997 sat
OUTPUT = 12,596,687 sat
FEE    =        310 sat
```

Before signing or broadcasting a manually constructed transaction,
always verify:

-   input amount
-   output amount
-   destination address/script
-   miner fee

Never rely only on raw hex looking correct.

------------------------------------------------------------------------

# Part 6 --- BIP143 Signature Hash

Because this is SegWit v0, the signing script constructs the signature
digest according to BIP143.

Conceptually it commits to:

``` text
version
hashPrevouts
hashSequence
outpoint
scriptCode
previous output amount
sequence
hashOutputs
locktime
SIGHASH type
```

The BIP143 preimage is double-SHA256 hashed:

``` text
SHA256(SHA256(BIP143 preimage))
```

This produces the 32-byte digest that gets signed.

With `SIGHASH_ALL`, the signature commits to all transaction outputs.

------------------------------------------------------------------------

# Part 7 --- Signing with Three Private Keys

Each required private key signs the transaction digest:

``` text
BIP143 digest
   |
   +--> Private Key 1 --> Signature 1
   +--> Private Key 2 --> Signature 2
   +--> Private Key 3 --> Signature 3
```

ECDSA produces a DER-encoded signature. For `SIGHASH_ALL`, byte `01` is
appended to each signature.

------------------------------------------------------------------------

# Part 8 --- Constructing the Witness

For traditional `CHECKMULTISIG` P2WSH, the witness stack is:

``` text
<empty item>
<signature 1>
<signature 2>
<signature 3>
<witnessScript>
```

The initial empty item exists because of the historical `CHECKMULTISIG`
extra-stack-item behavior.

The final SegWit transaction contains the normal transaction data plus
this witness.

------------------------------------------------------------------------

# Why Public-Key Order Matters

Multisig scripts contain public keys in a particular order. Changing the
order changes the witnessScript, which changes:

``` text
SHA256(witnessScript)
```

and therefore creates a different P2WSH output.

Some wallets use `sortedmulti()`, which sorts public keys
deterministically.

If recovery fails at the witness-script hash check, investigate key
ordering before assuming the keys themselves are wrong.

------------------------------------------------------------------------

# Recovery Checklist

1.  Make a copy of all wallet information.
2.  Work offline where possible.
3.  Identify the exact UTXO (`TXID:vout`).
4.  Verify the UTXO amount.
5.  Verify its `scriptPubKey`.
6.  Identify the wallet type.
7.  Identify the correct derivation paths.
8.  Derive the required private/public keys.
9.  Reconstruct the witnessScript.
10. Verify `SHA256(witnessScript)` against the P2WSH commitment.
11. Construct the unsigned transaction.
12. Verify the destination output.
13. Verify the amount.
14. Verify the miner fee.
15. Construct the BIP143 sighash.
16. Sign using the required keys.
17. Construct the witness.
18. Serialize the final transaction.
19. Decode/inspect the signed transaction independently before
    broadcasting.
20. Only then broadcast it.

------------------------------------------------------------------------

# Things I Must Never Forget

## A seed phrase does not directly identify one private key

It creates an HD tree:

``` text
Seed
 |
 +-- m/84'/...
 |
 +-- m/86'/...
 |
 +-- many other child keys
```

The derivation path matters.

## A BIP39 passphrase creates a different wallet

Correct mnemonic + wrong passphrase = wrong wallet.

## `scriptPubKey` and `witnessScript` are different

For P2WSH:

``` text
witnessScript
     |
     v
   SHA256
     |
     v
scriptPubKey
```

The `scriptPubKey` does not reveal the complete witnessScript.

## SegWit v0 signatures need the previous-output amount

When manually signing a SegWit v0 transaction, preserve the exact UTXO
amount.

## Verify before signing

The strongest check in this recovery was:

``` text
SHA256(reconstructed witnessScript)
==
hash committed to by the P2WSH output
```

If that fails, something about the reconstructed wallet is wrong.

## Never expose private keys during troubleshooting

Usually these are sufficient for debugging:

``` text
TXID
vout
scriptPubKey
public keys
witnessScript
derivation paths
transaction amounts
unsigned transaction
```

There is normally no reason to send somebody the seed phrase or private
keys.

------------------------------------------------------------------------

# Final Lesson

Bitcoin recovery is deterministic:

``` text
Mnemonic + Passphrase
        |
        v
     BIP39 Seed
        |
        v
       BIP32
        |
        v
Derivation Path
        |
        v
  Private Keys
        |
        v
   Public Keys
        |
        v
  Multisig Script
        |
        v
      P2WSH
        |
        v
      UTXO
        |
        v
 BIP143 Sighash
        |
        v
   ECDSA Signatures
        |
        v
      Witness
        |
        v
Signed Transaction
        |
        v
     Broadcast
```

As long as the original keys and enough information about how the wallet
was constructed are available, the wallet software itself is not what
controls the Bitcoin.

**The keys and Bitcoin's consensus rules do.**

------------------------------------------------------------------------

## Recommended Files to Keep Together

``` text
bitcoin-recovery/
├── README.md
├── derive_keys.py
└── sign_transaction.py
```

Do **not** put real seed phrases, BIP39 passphrases, or private keys in
this README.

For long-term recovery documentation, preserve non-secret metadata such
as:

-   wallet type
-   derivation paths
-   multisig policy (for example, 3-of-3)
-   public keys
-   descriptor, when available
-   witnessScript
-   network (mainnet/testnet)
-   notes explaining how the wallet was originally constructed

These details can make future recovery dramatically easier without
exposing the seed itself.
