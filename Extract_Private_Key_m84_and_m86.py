from bip_utils import (
    Bip39SeedGenerator,
    Bip84,
    Bip84Coins,
    Bip86,
    Bip86Coins,
    Bip44Changes,
    WifEncoder,
)

#Trezor Safe 7
#mnemonic = "robot riot reject slogan gap tray dress sad mushroom select general impose forest model online lesson suit build alarm stove upon laugh write glare"
#passphrase = "1234"

#Onekey
#mnemonic = "inch sponsor quote deny broccoli wreck album peace guess gold can jaguar peanut follow wool rice curious trigger exotic phone general lounge detect glove"
#passphrase = "1234"

#Ledger
mnemonic = "client trigger crunch van sphere finger where balance arrange away purchase rifle cover mountain shiver glory priority primary guide way vacant runway pipe neglect"
passphrase = "1234"

seed = Bip39SeedGenerator(mnemonic).Generate(passphrase)

# m/84'/0'/0'/0/0
bip84 = (
    Bip84.FromSeed(seed, Bip84Coins.BITCOIN)
    .Purpose()
    .Coin()
    .Account(0)
    .Change(Bip44Changes.CHAIN_EXT)
    .AddressIndex(0)
)

# m/86'/0'/0'/0/0
bip86 = (
    Bip86.FromSeed(seed, Bip86Coins.BITCOIN)
    .Purpose()
    .Coin()
    .Account(0)
    .Change(Bip44Changes.CHAIN_EXT)
    .AddressIndex(0)
)

print("\n=== BIP84 ===")
print("Path       : m/84'/0'/0'/0/0")
print("Private HEX:", bip84.PrivateKey().Raw().ToHex())
print("WIF        :", WifEncoder.Encode(bip84.PrivateKey().Raw().ToBytes()))
print("Public key :", bip84.PublicKey().RawCompressed().ToHex())
print("Address    :", bip84.PublicKey().ToAddress())

print("\n=== BIP86 ===")
print("Path       : m/86'/0'/0'/0/0")
print("Private HEX:", bip86.PrivateKey().Raw().ToHex())
print("WIF        :", WifEncoder.Encode(bip86.PrivateKey().Raw().ToBytes()))
print("Public key :", bip86.PublicKey().RawCompressed().ToHex())
print("Address    :", bip86.PublicKey().ToAddress())