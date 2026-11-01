"""Verify the storage optimization on a tiny local Qwen; no weights/downloads."""
import copy
import unittest
import torch
from transformers import AutoModel, Qwen3Config
from app.rag import CODE_ROOT  # exposes the shared code/RAG package
from RAG.Embeddings import use_cpu_float32_kernels


class EmbeddingRuntimeTests(unittest.TestCase):
    def test_native_bf16_storage_preserves_fp32_computation(self):
        torch.manual_seed(17)
        config = Qwen3Config(vocab_size=80, hidden_size=32, intermediate_size=64,
                             num_hidden_layers=2, num_attention_heads=4,
                             num_key_value_heads=2, head_dim=8, max_position_embeddings=128)
        compact = AutoModel.from_config(config, dtype=torch.bfloat16).eval()
        baseline = copy.deepcopy(compact).float()
        use_cpu_float32_kernels(compact, torch)
        self.assertEqual(compact.embed_tokens.weight.dtype, torch.bfloat16)
        self.assertEqual(compact.layers[0].self_attn.q_proj.weight.dtype, torch.bfloat16)
        self.assertEqual(compact.layers[0].input_layernorm.weight.dtype, torch.float32)
        ids = torch.tensor([[3, 4, 5, 6], [0, 0, 3, 7]])
        mask = torch.tensor([[1, 1, 1, 1], [0, 0, 1, 1]])
        with torch.inference_mode():
            first = baseline(input_ids=ids, attention_mask=mask, use_cache=False).last_hidden_state
            second = compact(input_ids=ids, attention_mask=mask, use_cache=False).last_hidden_state
        self.assertEqual(second.dtype, torch.float32)
        self.assertTrue(torch.allclose(first, second, atol=1e-6))


if __name__ == "__main__":
    unittest.main()
