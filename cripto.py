#!/usr/bin/env python3
"""Cifra o que o José manda pelo Telegram antes de ir para o repositório (que é público).

O GitHub cifra com a chave pública (telegram/chave_publica.pem). Só quem tem a chave
privada (guardada na área privada do José na Central JF) consegue abrir.

    python3 cripto.py fechar <arquivo> <saida>                 # usado pelo workflow
    python3 cripto.py abrir  <arquivo> <saida> <privada.pem>    # usado pelo CMO
"""
import base64, json, os, pathlib, sys
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

RAIZ = pathlib.Path(__file__).resolve().parent
OAEP = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


def fechar_bytes(dados: bytes) -> bytes:
    pub = serialization.load_pem_public_key((RAIZ / "telegram" / "chave_publica.pem").read_bytes())
    k = AESGCM.generate_key(bit_length=256)
    n = os.urandom(12)
    env = {"v": 1, "k": base64.b64encode(pub.encrypt(k, OAEP)).decode(), "n": base64.b64encode(n).decode(),
           "d": base64.b64encode(AESGCM(k).encrypt(n, dados, None)).decode()}
    return json.dumps(env).encode()


def abrir_bytes(env: bytes, pem: bytes) -> bytes:
    e = json.loads(env)
    priv = serialization.load_pem_private_key(pem, password=None)
    k = priv.decrypt(base64.b64decode(e["k"]), OAEP)
    return AESGCM(k).decrypt(base64.b64decode(e["n"]), base64.b64decode(e["d"]), None)


if __name__ == "__main__":
    modo, ent, sai = sys.argv[1:4]
    dados = pathlib.Path(ent).read_bytes()
    if modo == "fechar":
        out = fechar_bytes(dados)
    else:
        out = abrir_bytes(dados, pathlib.Path(sys.argv[4]).read_bytes())
    pathlib.Path(sai).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(sai).write_bytes(out)
