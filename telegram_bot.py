#!/usr/bin/env python3
"""Ponte entre o bot do Telegram e o CMO (agente da Central JF).

    python telegram_bot.py escutar [min]  # fica ouvindo: guarda, aciona o CMO na hora e manda as respostas
    python telegram_bot.py receber        # leitura única (reserva)
    python telegram_bot.py enviar         # manda o que o CMO deixou em outbox/

Mensagens recebidas (CIFRADAS com telegram/chave_publica.pem, porque o repositório é público):
  inbox/<update_id>.json  -> envelope cifrado de {"id", "data", "tipo", "texto", "transcricao", "midia": [{"arquivo", "tipo", "nome"}], "resposta_a"}
  A mídia (foto, áudio, vídeo, documento) vai cifrada para o ramo "midia", em <update_id>/<nome>.cifrado.
  Para abrir: python3 cripto.py abrir <arquivo> <saida> <chave privada>.

Mensagens para enviar:
  outbox/<qualquer>.json -> {"texto": "...", "imagens": ["outbox/a.png", ...]}
  (as imagens são caminhos no próprio repositório e são apagadas depois do envio)

Só aceita mensagens do chat do José (status.json -> telegram_chat ou TELEGRAM_CHAT_ID).
"""
import json, mimetypes, os, pathlib, subprocess, sys, time, urllib.parse, urllib.request, uuid
from cripto import fechar_bytes
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parent
TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
ARQ_API = f"https://api.telegram.org/file/bot{TOKEN}"
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
if not CHAT:
    try:
        CHAT = str(json.loads((RAIZ / "status.json").read_text()).get("telegram_chat") or "")
    except Exception:
        CHAT = ""
INBOX = RAIZ / "inbox"
OUTBOX = RAIZ / "outbox"
OFFSET = RAIZ / "telegram" / "offset.txt"
MIDIA = RAIZ / "_midia"          # worktree do ramo "midia" (montado pelo workflow)
LIMITE = 20 * 1024 * 1024        # a API de bots só baixa arquivos de até 20 MB


def api(metodo, dados=None, arquivos=None, timeout=60):
    url = f"{API}/{metodo}"
    if arquivos:
        corpo, tipo = multipart(dados or {}, arquivos)
        req = urllib.request.Request(url, data=corpo, headers={"Content-Type": tipo})
    elif dados is not None:
        req = urllib.request.Request(url, data=urllib.parse.urlencode(dados).encode())
    else:
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.loads(r.read().decode())
    if not resp.get("ok"):
        raise RuntimeError(resp.get("description", "erro do Telegram"))
    return resp["result"]


def multipart(campos, arquivos):
    limite = uuid.uuid4().hex
    partes = []
    for k, v in campos.items():
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for campo, caminho in arquivos.items():
        caminho = pathlib.Path(caminho)
        tipo = mimetypes.guess_type(caminho.name)[0] or "application/octet-stream"
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{campo}"; filename="{caminho.name}"\r\nContent-Type: {tipo}\r\n\r\n'.encode()
                      + caminho.read_bytes() + b"\r\n")
    partes.append(f"--{limite}--\r\n".encode())
    return b"".join(partes), f"multipart/form-data; boundary={limite}"


def enviar_texto(texto):
    for i in range(0, len(texto), 3900):          # limite do Telegram: 4096 caracteres
        api("sendMessage", {"chat_id": CHAT, "text": texto[i:i + 3900], "disable_web_page_preview": "true"})


def baixar(file_id, destino):
    info = api("getFile", {"file_id": file_id})
    if info.get("file_size", 0) > LIMITE:
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{ARQ_API}/{info['file_path']}", timeout=120) as r:
        destino.write_bytes(r.read())
    return True


_modelo = None
def transcrever(caminho):
    global _modelo
    try:
        if _modelo is None:
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "faster-whisper"], check=True)
            from faster_whisper import WhisperModel
            _modelo = WhisperModel("small", device="cpu", compute_type="int8")
        segs, _ = _modelo.transcribe(str(caminho), language="pt", vad_filter=True)
        return " ".join(s.text.strip() for s in segs).strip()
    except Exception as e:
        print("transcrição falhou:", e)
        return ""


def ler_offset():
    return int(OFFSET.read_text().strip() or 0) if OFFSET.exists() else 0


def buscar(offset, espera):
    return api("getUpdates", {"offset": offset, "timeout": espera,
                              "allowed_updates": json.dumps(["message", "edited_message"])}, timeout=espera + 30)


def guardar_updates(ups, offset):
    """Guarda (cifradas) as mensagens do José. Devolve (ids guardados, novo offset)."""
    INBOX.mkdir(exist_ok=True)
    novas = []
    for up in ups:
        offset = max(offset, up["update_id"] + 1)
        m = up.get("message") or up.get("edited_message")
        if not m or str(m.get("chat", {}).get("id")) != CHAT:
            continue
        uid = str(up["update_id"])
        reg = {"id": uid, "data": datetime.fromtimestamp(m["date"], timezone.utc).isoformat(),
               "tipo": "texto", "texto": m.get("text") or m.get("caption") or "", "transcricao": "", "midia": []}
        r = m.get("reply_to_message")
        if r:
            reg["resposta_a"] = (r.get("text") or r.get("caption") or "")[:1500]
        pasta = MIDIA / uid
        def guardar(fid, nome, tipo):
            ok = baixar(fid, pasta / nome)
            reg["midia"].append({"arquivo": f"{uid}/{nome}", "tipo": tipo, "nome": nome, "baixado": ok})
            return ok
        if m.get("voice") or m.get("audio"):
            a = m.get("voice") or m.get("audio")
            nome = "audio" + (".ogg" if m.get("voice") else pathlib.Path(a.get("file_name") or "a.mp3").suffix)
            reg["tipo"] = "audio"
            if guardar(a["file_id"], nome, a.get("mime_type", "audio/ogg")):
                reg["transcricao"] = transcrever(pasta / nome)
        if m.get("photo"):
            reg["tipo"] = "foto"
            guardar(m["photo"][-1]["file_id"], "foto.jpg", "image/jpeg")
        if m.get("video") or m.get("video_note"):
            v = m.get("video") or m.get("video_note")
            reg["tipo"] = "video"
            guardar(v["file_id"], "video.mp4", v.get("mime_type", "video/mp4"))
        if m.get("document"):
            d = m["document"]
            reg["tipo"] = "documento"
            guardar(d["file_id"], d.get("file_name") or "arquivo", d.get("mime_type", "application/octet-stream"))
        # o repositório é público: tudo que o José manda vai cifrado (só o CMO abre)
        for md in reg["midia"]:
            arq = MIDIA / md["arquivo"]
            if arq.exists():
                cif = arq.with_name(arq.name + ".cifrado")
                cif.write_bytes(fechar_bytes(arq.read_bytes()))
                arq.unlink()
                md["arquivo"] += ".cifrado"
        (INBOX / f"{uid}.json").write_bytes(fechar_bytes(json.dumps(reg, ensure_ascii=False, indent=1).encode()))
        novas.append(uid)
    OFFSET.parent.mkdir(exist_ok=True)
    OFFSET.write_text(str(offset))
    return novas, offset


def receber():
    """Leitura única (sem disparar o CMO). Usada como reserva."""
    if not TOKEN or not CHAT:
        print("Sem TELEGRAM_TOKEN ou chat; nada a fazer.")
        return
    offset = ler_offset()
    ups = buscar(offset, 0)
    novas, offset = guardar_updates(ups, offset) if ups else ([], offset)
    print(f"{len(novas)} mensagem(ns) guardada(s).")
    if novas:
        try:
            enviar_texto("📥 Recebi. O CMO responde em até 1 hora.")
        except Exception as e:
            print("aviso de recebimento falhou:", e)


# ---------------------------------------------------------------- modo escuta (conversa em tempo real)
CMO_TRIGGER = json.loads((RAIZ / "equipe" / "agentes.json").read_text()).get("cmo_aprovar", "")
FIRE_TOKEN = os.environ.get("CMO_FIRE_TOKEN", "").strip()


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=RAIZ, check=check, capture_output=True, text=True)


def salvar_e_subir(msg):
    """Commita mídia (ramo midia) e caixa (main) e dá push, com retentativas."""
    if (MIDIA / ".git").exists():
        subprocess.run(["git", "add", "-A", "."], cwd=MIDIA)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=MIDIA).returncode:
            subprocess.run(["git", "commit", "-qm", "Mídia do Telegram"], cwd=MIDIA)
            for _ in range(3):
                if subprocess.run(["git", "push", "-q", "origin", "midia"], cwd=MIDIA).returncode == 0:
                    break
                time.sleep(2)
    git("add", "-A", "inbox", "outbox", "telegram")
    if git("diff", "--cached", "--quiet", check=False).returncode == 0:
        return
    git("commit", "-qm", msg)
    for _ in range(5):
        if git("pull", "-q", "--rebase", "--autostash", "origin", "main", check=False).returncode == 0 and \
           git("push", "-q", "origin", "HEAD:main", check=False).returncode == 0:
            return
        time.sleep(3)


def disparar_cmo(ids):
    if not (FIRE_TOKEN and CMO_TRIGGER):
        return False
    corpo = json.dumps({"text": "Mensagens novas do José no Telegram (cifradas no repositório): "
                        + ", ".join(f"inbox/{i}.json" for i in ids)}).encode()
    req = urllib.request.Request(
        f"https://api.anthropic.com/v1/claude_code/routines/{CMO_TRIGGER}/fire", data=corpo, method="POST",
        headers={"Authorization": f"Bearer {FIRE_TOKEN}", "anthropic-beta": "experimental-cc-routine-2026-04-01",
                 "anthropic-version": "2023-06-01", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("CMO acionado:", r.status)
            return True
    except Exception as e:
        print("não consegui acionar o CMO:", e)
        return False


def escutar(minutos=55):
    """Fica ouvindo o bot: guarda cada mensagem, aciona o CMO na hora e manda as respostas dele."""
    if not TOKEN or not CHAT:
        print("Sem TELEGRAM_TOKEN ou chat.")
        return
    fim = time.time() + minutos * 60
    offset = ler_offset()
    aguardando_ate = 0
    while time.time() < fim:
        # respostas do CMO
        git("pull", "-q", "--rebase", "--autostash", "origin", "main", check=False)
        if any(OUTBOX.glob("*.json")):
            enviar()
            salvar_e_subir("Telegram: respostas do CMO enviadas")
            aguardando_ate = 0
        # mensagens do José
        espera = 3 if time.time() < aguardando_ate else 20
        try:
            ups = buscar(offset, espera)
        except Exception as e:
            print("getUpdates falhou:", e)
            time.sleep(5)
            continue
        if ups:
            time.sleep(4)                       # junta mensagens em sequência (ex.: foto + texto)
            try:
                ups += buscar(max(u["update_id"] for u in ups) + 1, 0)
            except Exception:
                pass
            novas, offset = guardar_updates(ups, offset)
            if novas:
                try:
                    api("sendChatAction", {"chat_id": CHAT, "action": "typing"})
                except Exception:
                    pass
                salvar_e_subir("Telegram: caixa do CMO")
                if disparar_cmo(novas):
                    aguardando_ate = time.time() + 6 * 60
                else:
                    try:
                        enviar_texto("📥 Recebi. Respondo em até 1 hora.")
                    except Exception:
                        pass
        elif time.time() < aguardando_ate:
            try:
                api("sendChatAction", {"chat_id": CHAT, "action": "typing"})
            except Exception:
                pass


def enviar():
    if not TOKEN or not CHAT or not OUTBOX.exists():
        return
    for arq in sorted(OUTBOX.glob("*.json")):
        try:
            msg = json.loads(arq.read_text())
        except Exception:
            arq.unlink()
            continue
        imgs = [RAIZ / p for p in msg.get("imagens", []) if (RAIZ / p).exists()]
        texto = (msg.get("texto") or "").strip()
        try:
            if imgs:
                for i in range(0, len(imgs), 10):
                    lote = imgs[i:i + 10]
                    if len(lote) == 1:
                        api("sendPhoto", {"chat_id": CHAT}, {"photo": lote[0]})
                    else:
                        media = [{"type": "photo", "media": f"attach://f{k}"} for k in range(len(lote))]
                        api("sendMediaGroup", {"chat_id": CHAT, "media": json.dumps(media)},
                            {f"f{k}": p for k, p in enumerate(lote)}, timeout=180)
            if texto:
                enviar_texto(texto)
        except Exception as e:
            print(f"falhou ao enviar {arq.name}: {e}")
            continue
        for p in imgs:
            p.unlink(missing_ok=True)
        arq.unlink()
        time.sleep(1)


if __name__ == "__main__":
    if sys.argv[1] == "escutar":
        escutar(int(sys.argv[2]) if len(sys.argv) > 2 else 55)
    else:
        {"receber": receber, "enviar": enviar}[sys.argv[1]]()
