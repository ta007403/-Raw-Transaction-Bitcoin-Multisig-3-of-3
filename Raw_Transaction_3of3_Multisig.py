import hashlib
from ecdsa import SigningKey, SECP256k1
from ecdsa.util import sigencode_der_canonize


# ============================================================
# CONFIGURATION
# ============================================================

# Your unsigned transaction
RAW_TX = (
    "0200000001"
    "cf60de088086de832432d6685c681c842fcbbd6ff1c7763e1e21e0145603bf3f"
    "01000000"
    "00"
    "fdffffff"
    "01"
    "cf35c0000000000"
    "16"
    "00142efd075007e68d232525c8fed0f086cfff9c95b5"
    "4ebb0e00"
)

# Amount of 3fbf...:1
PREVOUT_AMOUNT = 12_596_997

# P2WSH scriptPubKey of the UTXO
PREVOUT_SCRIPT_PUBKEY = (
    "00205cf170ca5a4d3be76d576317f3ede85ea4cdba30798484927dab6ea442877132"
)

# Put your THREE 32-byte private keys here.
#
# IMPORTANT:
# The ORDER matters for a normal multisig witnessScript.
#
PRIVATE_KEYS = [
    "e778b15aaca9b726e839f3e967dc6ff6508d7831dd8d32eaafe5bd5920144a2c",
    "1cbd4a087c0e649e6d1cfac13340b8f0356e510c7c0c31d0762b9fb081051a85",
    "3b6f4debed1cc18eeb23923da378da62aa9ee33e3493788d9637f44bf8eddf5f",
]


# ============================================================
# BASIC FUNCTIONS
# ============================================================

def sha256(data):
    return hashlib.sha256(data).digest()


def sha256d(data):
    return sha256(sha256(data))


def little_endian(value, length):
    return value.to_bytes(length, "little")


def compact_size(n):
    if n < 0xfd:
        return bytes([n])
    elif n <= 0xffff:
        return b"\xfd" + little_endian(n, 2)
    elif n <= 0xffffffff:
        return b"\xfe" + little_endian(n, 4)
    else:
        return b"\xff" + little_endian(n, 8)


# ============================================================
# PUBLIC KEY GENERATION
# ============================================================

def privkey_to_compressed_pubkey(privkey_hex):

    priv = bytes.fromhex(privkey_hex)

    sk = SigningKey.from_string(
        priv,
        curve=SECP256k1
    )

    point = sk.verifying_key.pubkey.point

    x = point.x()
    y = point.y()

    prefix = b"\x02" if y % 2 == 0 else b"\x03"

    return prefix + x.to_bytes(32, "big")


pubkeys = [
    privkey_to_compressed_pubkey(k)
    for k in PRIVATE_KEYS
]


print("\n=== PUBLIC KEYS ===")

for i, pub in enumerate(pubkeys, 1):
    print(f"KEY {i}: {pub.hex()}")


# ============================================================
# CREATE 3-of-3 WITNESS SCRIPT
#
# OP_3
# PUSH33 pubkey1
# PUSH33 pubkey2
# PUSH33 pubkey3
# OP_3
# OP_CHECKMULTISIG
# ============================================================

witness_script = (
    b"\x53"
    + b"\x21" + pubkeys[0]
    + b"\x21" + pubkeys[1]
    + b"\x21" + pubkeys[2]
    + b"\x53"
    + b"\xae"
)


print("\n=== WITNESS SCRIPT ===")
print(witness_script.hex())


# ============================================================
# VERIFY P2WSH
# ============================================================

witness_hash = sha256(witness_script)

expected_hash = bytes.fromhex(
    PREVOUT_SCRIPT_PUBKEY
)[2:]


print("\nCalculated SHA256:")
print(witness_hash.hex())

print("\nExpected SHA256:")
print(expected_hash.hex())


if witness_hash != expected_hash:

    print("\nERROR!")
    print("The private keys / public-key order do NOT correspond")
    print("to the P2WSH UTXO.")

    raise SystemExit(1)


print("\nP2WSH MATCH! Safe to continue signing.")


# ============================================================
# BIP143 SIGHASH
# ============================================================

SIGHASH_ALL = 1


# Previous outpoint
prev_txid = bytes.fromhex(
    "3fbf035614e0211e3e76c7f16fbdcb2f841c685c68d6322483de868008de60cf"
)[::-1]

prev_vout = little_endian(1, 4)

outpoint = prev_txid + prev_vout


# Sequence
sequence = bytes.fromhex("fdffffff")


# Output from unsigned transaction
output_amount = little_endian(12_596_687, 8)

output_script = bytes.fromhex(
    "00142efd075007e68d232525c8fed0f086cfff9c95b5"
)

serialized_output = (
    output_amount
    + compact_size(len(output_script))
    + output_script
)


# BIP143 hashes
hash_prevouts = sha256d(outpoint)

hash_sequence = sha256d(sequence)

hash_outputs = sha256d(serialized_output)


# Transaction version
version = little_endian(2, 4)


# Locktime from your unsigned transaction
locktime = bytes.fromhex("4ebb0e00")


# scriptCode = witnessScript
script_code = (
    compact_size(len(witness_script))
    + witness_script
)


# Construct BIP143 preimage
preimage = (
    version
    + hash_prevouts
    + hash_sequence
    + outpoint
    + script_code
    + little_endian(PREVOUT_AMOUNT, 8)
    + sequence
    + hash_outputs
    + locktime
    + little_endian(SIGHASH_ALL, 4)
)


sighash = sha256d(preimage)


print("\n=== BIP143 ===")
print("Preimage:")
print(preimage.hex())

print("\nSIGHASH:")
print(sighash.hex())


# ============================================================
# SIGN WITH ALL THREE KEYS
# ============================================================

signatures = []


for i, privkey_hex in enumerate(PRIVATE_KEYS, 1):

    sk = SigningKey.from_string(
        bytes.fromhex(privkey_hex),
        curve=SECP256k1
    )

    der_signature = sk.sign_digest_deterministic(
        sighash,
        hashfunc=hashlib.sha256,
        sigencode=sigencode_der_canonize,
    )

    # Append SIGHASH_ALL
    signature = der_signature + b"\x01"

    signatures.append(signature)

    print(f"\nSignature {i}:")
    print(signature.hex())


# ============================================================
# CREATE SEGWIT WITNESS
#
# CHECKMULTISIG witness:
#
# 00
# signature1
# signature2
# signature3
# witnessScript
#
# ============================================================

witness_items = [
    b"",
    signatures[0],
    signatures[1],
    signatures[2],
    witness_script,
]


witness = compact_size(len(witness_items))

for item in witness_items:
    witness += compact_size(len(item))
    witness += item


# ============================================================
# BUILD FINAL SEGWIT TRANSACTION
# ============================================================

final_tx = (
    version
    + b"\x00\x01"                 # SegWit marker + flag
    + b"\x01"                     # input count
    + outpoint
    + b"\x00"                     # empty scriptSig
    + sequence
    + b"\x01"                     # output count
    + serialized_output
    + witness
    + locktime
)


print("\n============================================")
print("FINAL SIGNED TRANSACTION")
print("============================================")

print(final_tx.hex())