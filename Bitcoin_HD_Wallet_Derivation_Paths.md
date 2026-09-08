# Understanding Bitcoin HD Wallet Derivation Paths

## What does `m/84'/0'/0'/0/0` actually mean?

A Bitcoin derivation path such as:

``` text
m/84'/0'/0'/0/0
```

is **not ASCII data being hashed**, and `/` is **not division**.

It is human-readable notation describing a route through a deterministic
BIP32 hierarchical wallet tree.

For example:

``` text
m/84'/0'/0'/0/0
m/84'/0'/0'/0/1
m/84'/0'/0'/0/2
```

all start from the same master node and follow the same route until the
final child index.

------------------------------------------------------------------------

# 1. From BIP39 Mnemonic to BIP32 Master Node

The process begins with:

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
```

BIP32 then creates the master node using:

``` text
HMAC-SHA512(
    key  = "Bitcoin seed",
    data = BIP39_seed
)
```

Here, `"Bitcoin seed"` really is a byte string represented by those
characters.

HMAC-SHA512 produces 64 bytes:

``` text
64 bytes
+-----------------------+-----------------------+
| first 32 bytes        | last 32 bytes         |
|                       |                       |
| Master private key    | Master chain code     |
| k                     | c                     |
+-----------------------+-----------------------+
```

This pair is the master extended private-key node represented by:

``` text
m
```

So `m` itself is not the ASCII character `m` passed into every
derivation calculation. It is notation meaning:

> Start from the BIP32 master private node.

------------------------------------------------------------------------

# 2. What does `/` mean?

The slash is notation for:

> Derive the next child node.

Therefore:

``` text
m/84'
```

means:

> Start at `m` and derive child 84 using hardened derivation.

And:

``` text
m/84'/0'
```

means:

> Take the result of `m/84'` and derive hardened child 0 from it.

The `/` character itself is not used as division and is not inserted
into the cryptographic HMAC calculation.

------------------------------------------------------------------------

# 3. What does the apostrophe `'` mean?

The apostrophe means **hardened derivation**.

For example:

``` text
84'
```

means hardened child 84.

BIP32 represents hardened indexes by adding:

``` text
2^31 = 2147483648
```

Therefore:

``` text
84'
=
84 + 2^31
=
2147483732
=
0x80000054
```

Serialized as a 32-bit big-endian integer:

``` text
80 00 00 54
```

Similarly:

``` text
0'
=
0 + 2^31
=
2147483648
=
0x80000000
```

So the literal characters:

``` text
/
8
4
'
```

are not being hashed together.

They are human-readable instructions telling wallet software which BIP32
calculation to perform.

------------------------------------------------------------------------

# 4. Walking Through BIP84

Consider:

``` text
m/84'/0'/0'/0/0
```

It can be visualized as:

``` text
m
 |
 +-- 84'    hardened
      |
      +-- 0'    hardened
           |
           +-- 0'    hardened
                |
                +-- 0     normal
                     |
                     +-- 0     normal
```

Each level derives a new BIP32 node.

## `m/84'`

Start with the master node and derive hardened child 84.

## `m/84'/0'`

Take the previous result and derive hardened child 0.

## `m/84'/0'/0'`

Again derive hardened child 0.

## `m/84'/0'/0'/0`

Now derive **normal child 0**.

There is no apostrophe, so this is non-hardened derivation.

## `m/84'/0'/0'/0/0`

Finally derive normal child 0 from the receiving branch.

------------------------------------------------------------------------

# 5. Why `/0/0`, `/0/1`, `/0/2`?

These paths:

``` text
m/84'/0'/0'/0/0
m/84'/0'/0'/0/1
m/84'/0'/0'/0/2
```

share the same parent:

``` text
m/84'/0'/0'/0
```

Then different child indexes are derived:

``` text
                     m/84'/0'/0'/0
                         |
              +----------+----------+
              |          |          |
           CKD(0)     CKD(1)     CKD(2)
              |          |          |
              v          v          v
            /0/0       /0/1       /0/2
              |          |          |
              v          v          v
          private     private     private
           key 0       key 1       key 2
              |          |          |
              v          v          v
          public      public      public
           key 0       key 1       key 2
              |          |          |
              v          v          v
           bc1q...     bc1q...     bc1q...
```

This is how an HD wallet can deterministically generate many receiving
addresses.

------------------------------------------------------------------------

# 6. What Is Stored in a BIP32 Node?

Conceptually, a private BIP32 node contains important information
including:

``` text
Private key
+
Chain code
```

For child derivation, the chain code is extremely important.

A private key alone and a BIP32 extended private key are therefore not
exactly the same thing.

An extended key contains the information needed to continue
deterministic child derivation.

------------------------------------------------------------------------

# 7. Normal Child Private-Key Derivation

Suppose a parent node contains:

``` text
parent private key = k_par
parent chain code  = c_par
```

For a normal, non-hardened child such as:

``` text
/0
```

BIP32 constructs data using the compressed parent public key and child
index:

``` text
data =
    compressed_parent_public_key
    ||
    child_index
```

Then:

``` text
I = HMAC-SHA512(
        key  = parent_chain_code,
        data = data
    )
```

The 64-byte result is split:

``` text
I = IL || IR

IL = first 32 bytes
IR = last 32 bytes
```

The child private key is calculated:

``` text
k_child =
    (parse256(IL) + k_parent) mod n
```

where `n` is the order of the secp256k1 elliptic curve group.

The new child chain code is:

``` text
c_child = IR
```

So each derivation produces another node that can itself derive more
children.

------------------------------------------------------------------------

# 8. Hardened Child Private-Key Derivation

Hardened derivation is different.

For:

``` text
m/84'
```

BIP32 does not use the parent public key in the HMAC input.

Instead:

``` text
data =
    0x00
    ||
    parent_private_key
    ||
    hardened_child_index
```

For child `84'`, conceptually:

``` text
HMAC-SHA512(
    key  = parent_chain_code,
    data =
        00
        + parent_private_key
        + 80000054
)
```

Again:

``` text
I = IL || IR
```

and:

``` text
child_private_key =
    (parse256(IL) + parent_private_key) mod n
```

while:

``` text
child_chain_code = IR
```

The important difference is that hardened derivation requires the parent
**private key**.

------------------------------------------------------------------------

# 9. Normal vs Hardened Derivation

A useful conceptual comparison:

``` text
NORMAL CHILD

Parent private key
      |
      +--> Parent PUBLIC key ----+
      |                          |
Parent chain code ---------------+--> HMAC-SHA512
                                  |
Child index ---------------------+
                                  |
                                  v
                               IL || IR
                                  |
                     +------------+------------+
                     |                         |
                     v                         v
             child private key          child chain code
```

Versus:

``` text
HARDENED CHILD

Parent PRIVATE key -------------+
                                 |
Parent chain code --------------+--> HMAC-SHA512
                                 |
Hardened child index -----------+
                                 |
                                 v
                              IL || IR
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
            child private key          child chain code
```

This difference is one reason hardened derivation is used at important
levels of standard wallet paths.

------------------------------------------------------------------------

# 10. The Full BIP84 Calculation Tree

Starting from the mnemonic:

``` text
Mnemonic
   |
   | PBKDF2-HMAC-SHA512
   v
BIP39 Seed (64 bytes)
   |
   | HMAC-SHA512("Bitcoin seed", seed)
   v
+--------------------------+
| m                        |
| Master Private Key       |
| Master Chain Code        |
+--------------------------+
            |
            | CKDpriv(84 + 2^31)
            v
+--------------------------+
| m/84'                    |
+--------------------------+
            |
            | CKDpriv(0 + 2^31)
            v
+--------------------------+
| m/84'/0'                 |
+--------------------------+
            |
            | CKDpriv(0 + 2^31)
            v
+--------------------------+
| m/84'/0'/0'              |
+--------------------------+
            |
            | CKDpriv(0)
            v
+--------------------------+
| m/84'/0'/0'/0            |
+--------------------------+
       /       |       \
      /        |        \
 CKD(0)     CKD(1)     CKD(2)
    |          |          |
    v          v          v
 /0/0       /0/1       /0/2
    |          |          |
    v          v          v
Private     Private     Private
 Key 0       Key 1       Key 2
    |          |          |
    v          v          v
Public      Public      Public
 Key 0       Key 1       Key 2
    |          |          |
    v          v          v
bc1q...     bc1q...     bc1q...
```

Each arrow is a cryptographic child-key derivation calculation.

It is **not division** and it is **not simply hashing the textual
path**.

------------------------------------------------------------------------

# 11. How to Read a Derivation Path

For:

``` text
m/84'/0'/0'/0/2
```

read it as:

> Start from the master private node → hardened child 84 → hardened
> child 0 → hardened child 0 → normal child 0 → normal child 2.

A useful notation table:

  Notation   Meaning
  ---------- -----------------------------
  `m`        BIP32 master private node
  `/`        move/derive to a child node
  `84`       child index 84
  `84'`      hardened child index 84
  `0'`       hardened child index 0
  `0`        normal child index 0
  `1`        normal child index 1
  `2`        normal child index 2

------------------------------------------------------------------------

# 12. Why BIP84 Uses These Numbers

A common Bitcoin mainnet BIP84 account path is:

``` text
m / 84' / 0' / 0' / change / address_index
```

Conceptually:

``` text
84' = purpose
0'  = Bitcoin mainnet coin type
0'  = account 0
0   = external/receiving chain
0   = address index
```

Therefore:

``` text
m/84'/0'/0'/0/0
```

means approximately:

> BIP84 → Bitcoin → account 0 → receiving addresses → address 0.

And:

``` text
m/84'/0'/0'/0/25
```

means address index 25 on that same receiving branch.

The change branch commonly uses:

``` text
m/84'/0'/0'/1/0
```

where `/1` selects the internal/change chain.

------------------------------------------------------------------------

# 13. Why HD Wallets Are Powerful

A wallet does not need to randomly generate and separately back up
thousands of unrelated private keys.

Instead:

``` text
Mnemonic
   |
   v
Seed
   |
   v
Master node
   |
   +--> Account
          |
          +--> Receiving address 0
          +--> Receiving address 1
          +--> Receiving address 2
          +--> Receiving address 3
          +--> ...
```

The same mnemonic and passphrase reproduce the same master node.

The same master node plus the same derivation path reproduces the same
child key.

Therefore:

``` text
same mnemonic
+ same passphrase
+ same derivation path
=
same private key
```

This determinism is the foundation of modern HD wallet recovery.

------------------------------------------------------------------------

# 14. Important Recovery Lesson

Knowing only:

``` text
12 or 24 seed words
```

may not be enough to understand where a particular wallet application
placed funds.

Useful recovery information includes:

``` text
BIP39 mnemonic
BIP39 passphrase
network
derivation standard
derivation path
account number
change/receiving branch
address index
multisig policy, if applicable
wallet descriptor, if available
```

For multisig, descriptors and public-key derivation information can be
especially important.

------------------------------------------------------------------------

# 15. The Main Thing to Remember

When you see:

``` text
m/84'/0'/0'/0/0
```

do **not** think:

``` text
"m slash 84 slash 0..."
```

as data being hashed.

Think:

``` text
MASTER NODE
    |
    v
derive hardened child 84
    |
    v
derive hardened child 0
    |
    v
derive hardened child 0
    |
    v
derive normal child 0
    |
    v
derive normal child 0
    |
    v
PRIVATE KEY
```

The path is simply a compact human-readable instruction describing which
branches of the BIP32 mathematical tree to follow.

------------------------------------------------------------------------

## One-Sentence Summary

> **`m/84'/0'/0'/0/0` is not an ASCII string used as a key and `/` is
> not division; it is notation telling a BIP32 wallet to repeatedly
> perform deterministic HMAC-SHA512/secp256k1 child-key derivations,
> starting from the master node and following the specified child
> indexes.**

------------------------------------------------------------------------

<img width="768" height="356" alt="image" src="https://github.com/user-attachments/assets/88de1ed3-9d01-4f24-b5ab-b9b37bd0c26c" />
