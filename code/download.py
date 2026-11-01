"""Explicit model download into code/models, separate from server requests."""
import argparse
from hashlib import sha256
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.config import Settings

def file_digest(file):
    digest = sha256()
    with file.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def download_modelscope(settings):
    """Download the official Qwen weights with content-hash verification."""
    import httpx
    model_id = settings.embedding_model
    target = settings.embedding_cache_dir / model_id.split("/")[-1]
    target.mkdir(parents=True, exist_ok=True)
    api = "https://modelscope.cn/api/v1/models/" + model_id
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        listing = client.get(api + "/repo/files", params={"Recursive": "true", "Revision": "master"})
        listing.raise_for_status()
        for item in listing.json()["Data"]["Files"]:
            name = item["Path"]
            if item["Type"] != "blob" or "/" in name or not name.endswith((".json", ".safetensors", ".txt")):
                continue
            file = target / name
            if file.is_file() and file_digest(file) == item["Sha256"]:
                continue
            print("下载 " + name, flush=True)
            temporary = file.with_suffix(file.suffix + ".part")
            digest = sha256()
            with client.stream("GET", api + "/repo", params={"Revision": "master", "FilePath": name}) as response:
                response.raise_for_status()
                with temporary.open("wb") as stream:
                    for block in response.iter_bytes(1024 * 1024):
                        stream.write(block)
                        digest.update(block)
            if digest.hexdigest() != item["Sha256"]:
                raise ValueError("模型下载校验失败：" + name)
            temporary.replace(file)
    print("模型已下载并校验：" + str(target))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["huggingface", "modelscope"], default="huggingface")
    args = parser.parse_args()
    settings = Settings.from_env()
    if Path(settings.embedding_model).is_dir():
        print("已配置本地模型目录，无需下载。")
    elif args.source == "modelscope":
        download_modelscope(settings)
    else:
        from huggingface_hub import snapshot_download
        print(snapshot_download(settings.embedding_model, cache_dir=str(settings.embedding_cache_dir),
                                allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model"]))
