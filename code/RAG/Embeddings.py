"""Qwen3 embeddings using the official last-token pooling recipe."""
from time import perf_counter

QUERY_INSTRUCTION = "Instruct: Given a question about Chinese herbal medicine, retrieve relevant passages that answer it.\nQuery: "


def use_cpu_float32_kernels(model, torch):
    """Keep native BF16 weights; cast only each active operation to FP32."""
    from types import MethodType
    functional = torch.nn.functional

    def linear(layer, inputs):
        return functional.linear(inputs.float(), layer.weight.float(),
                                 layer.bias.float() if layer.bias is not None else None)

    def embedding(layer, inputs):
        return functional.embedding(inputs, layer.weight, layer.padding_idx, layer.max_norm,
                                    layer.norm_type, layer.scale_grad_by_freq, layer.sparse).float()

    for module in model.modules():
        if isinstance(module, torch.nn.Linear):
            module.forward = MethodType(linear, module)
        elif isinstance(module, torch.nn.Embedding):
            module.forward = MethodType(embedding, module)
    for module in model.modules():
        if module.__class__.__name__ == "Qwen3RMSNorm":
            module.float()


class QwenEmbedding:
    def __init__(self, model_path, device="cpu", cache_dir=None, max_length=1024, cpu_storage="bf16"):
        started = perf_counter()
        import torch
        from transformers import AutoModel, AutoTokenizer
        imports_done = perf_counter()

        self.torch = torch
        self.device = device
        self.max_length = max_length
        if device == "cpu":
            torch.set_num_threads(min(torch.get_num_threads(), 4))
        # Download explicitly with download.py; HTTP requests never fetch models.
        options = dict(local_files_only=True, trust_remote_code=False, cache_dir=cache_dir)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, padding_side="left", **options)
        tokenizer_done = perf_counter()
        compact_cpu = device == "cpu" and cpu_storage == "bf16"
        self.model = AutoModel.from_pretrained(
            model_path, dtype=torch.bfloat16 if compact_cpu or device != "cpu" else torch.float32,
            **options,
        ).to(device).eval()
        weights_done = perf_counter()
        if compact_cpu:
            use_cpu_float32_kernels(self.model, torch)
        self.load_timings = {"imports_ms": round((imports_done - started) * 1000, 2),
                             "tokenizer_ms": round((tokenizer_done - imports_done) * 1000, 2),
                             "weights_ms": round((weights_done - tokenizer_done) * 1000, 2),
                             "total_ms": round((perf_counter() - started) * 1000, 2)}

    def get_embeddings(self, texts, batch_size=4):
        torch = self.torch
        result = []
        for start in range(0, len(texts), batch_size):
            inputs = self.tokenizer(texts[start:start + batch_size], padding=True, truncation=True,
                                    max_length=self.max_length, return_tensors="pt").to(self.device)
            with torch.inference_mode():
                # Embedding is one forward pass; retaining generation KV caches
                # wastes memory on CPU and can trigger paging on an 8 GB machine.
                hidden = self.model(**inputs, use_cache=False).last_hidden_state
                # Left padding makes the last token the last non-padding token.
                vectors = torch.nn.functional.normalize(hidden[:, -1], p=2, dim=1)
                result.extend(vectors.float().cpu().numpy().tolist())
        return result

    def get_embedding(self, text):
        return self.get_embeddings([text])[0]

    def embed_query(self, text):
        return self.get_embedding(QUERY_INSTRUCTION + text)
