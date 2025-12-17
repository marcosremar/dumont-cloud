# nvCOMP GPU Compression Benchmark Results

**GPU**: NVIDIA RTX 3090 (24GB)
**Model**: Qwen2.5-0.5B
**CUDA Version**: 13.0
**nvCOMP Version**: 5.1.0

## Comparison Table

| Algorithm | Compression Ratio | Compressed Size | Comp Speed | Decomp Speed | Comp Time | Decomp Time |
|-----------|-------------------|-----------------|------------|--------------|-----------|-------------|
| LZ4       | 1.00x | 941.4 MB        | 2.57 GB/s  | 71.15 GB/s   | 0.358s | 0.013s |
| Snappy    | 0.99x | 947.2 MB        | 14.16 GB/s | 78.69 GB/s   | 0.065s | 0.012s |
| GDeflate  | 1.28x | 738.1 MB        | 2.13 GB/s  | 37.23 GB/s   | 0.433s | 0.025s |
| ANS       | 1.26x | 747.5 MB        | 50.87 GB/s | 101.90 GB/s  | 0.018s | 0.009s |
| Zstd      | 1.28x | 735.4 MB        | 1.76 GB/s  | 12.72 GB/s   | 0.524s | 0.072s |
| Cascaded  | 1.00x | 942.7 MB        | 41.91 GB/s | 102.71 GB/s  | 0.022s | 0.009s |
| Bitcomp   | 1.00x | 943.9 MB        | 68.56 GB/s | 64.79 GB/s   | 0.013s | 0.014s |
| Deflate   | 1.28x | 735.4 MB        | 1.97 GB/s  | 7.24 GB/s    | 0.468s | 0.127s |

## Best for Different Use Cases

- **Best Compression Ratio**: Deflate (1.28x) - Saves the most storage space
- **Fastest Compression**: Bitcomp (68.56 GB/s) - Best for backup operations
- **Fastest Decompression**: Cascaded (102.71 GB/s) - Best for restore operations

## Recommendations for 70GB Workspace


### LZ4
- Compressed size: ~71609 MB (69.9 GB)
- Estimated compression time: ~27s (0.5 min)
- Estimated decompression time: ~1s (0.0 min)
- R2 storage cost: ~$1.05/month

### Snappy
- Compressed size: ~72049 MB (70.4 GB)
- Estimated compression time: ~5s (0.1 min)
- Estimated decompression time: ~1s (0.0 min)
- R2 storage cost: ~$1.06/month

### GDeflate
- Compressed size: ~56144 MB (54.8 GB)
- Estimated compression time: ~33s (0.5 min)
- Estimated decompression time: ~2s (0.0 min)
- R2 storage cost: ~$0.82/month

### ANS
- Compressed size: ~56859 MB (55.5 GB)
- Estimated compression time: ~1s (0.0 min)
- Estimated decompression time: ~1s (0.0 min)
- R2 storage cost: ~$0.83/month

### Zstd
- Compressed size: ~55941 MB (54.6 GB)
- Estimated compression time: ~40s (0.7 min)
- Estimated decompression time: ~6s (0.1 min)
- R2 storage cost: ~$0.82/month

### Cascaded
- Compressed size: ~71706 MB (70.0 GB)
- Estimated compression time: ~2s (0.0 min)
- Estimated decompression time: ~1s (0.0 min)
- R2 storage cost: ~$1.05/month

### Bitcomp
- Compressed size: ~71802 MB (70.1 GB)
- Estimated compression time: ~1s (0.0 min)
- Estimated decompression time: ~1s (0.0 min)
- R2 storage cost: ~$1.05/month

### Deflate
- Compressed size: ~55937 MB (54.6 GB)
- Estimated compression time: ~36s (0.6 min)
- Estimated decompression time: ~10s (0.2 min)
- R2 storage cost: ~$0.82/month

## Raw Results

```json
[
  {
    "name": "LZ4",
    "original_size": 988097824,
    "compressed_size": 987123337,
    "ratio": 1.0009871988266041,
    "comp_time": 0.3575425148010254,
    "decomp_time": 0.012933492660522461,
    "comp_speed": "2.57 GB/s",
    "decomp_speed": "71.15 GB/s"
  },
  {
    "name": "Snappy",
    "original_size": 988097824,
    "compressed_size": 993184199,
    "ratio": 0.9948787193703632,
    "comp_time": 0.0649712085723877,
    "decomp_time": 0.011693954467773438,
    "comp_speed": "14.16 GB/s",
    "decomp_speed": "78.69 GB/s"
  },
  {
    "name": "GDeflate",
    "original_size": 988097824,
    "compressed_size": 773938828,
    "ratio": 1.2767130789308325,
    "comp_time": 0.432905912399292,
    "decomp_time": 0.024718761444091797,
    "comp_speed": "2.13 GB/s",
    "decomp_speed": "37.23 GB/s"
  },
  {
    "name": "ANS",
    "original_size": 988097824,
    "compressed_size": 783791604,
    "ratio": 1.2606639557726111,
    "comp_time": 0.01808905601501465,
    "decomp_time": 0.009031057357788086,
    "comp_speed": "50.87 GB/s",
    "decomp_speed": "101.90 GB/s"
  },
  {
    "name": "Zstd",
    "original_size": 988097824,
    "compressed_size": 771141806,
    "ratio": 1.2813438673820259,
    "comp_time": 0.5243017673492432,
    "decomp_time": 0.07234477996826172,
    "comp_speed": "1.76 GB/s",
    "decomp_speed": "12.72 GB/s"
  },
  {
    "name": "Cascaded",
    "original_size": 988097824,
    "compressed_size": 988459784,
    "ratio": 0.9996338141360337,
    "comp_time": 0.02195572853088379,
    "decomp_time": 0.00896000862121582,
    "comp_speed": "41.91 GB/s",
    "decomp_speed": "102.71 GB/s"
  },
  {
    "name": "Bitcomp",
    "original_size": 988097824,
    "compressed_size": 989781972,
    "ratio": 0.9982984656746203,
    "comp_time": 0.01342320442199707,
    "decomp_time": 0.014202356338500977,
    "comp_speed": "68.56 GB/s",
    "decomp_speed": "64.79 GB/s"
  },
  {
    "name": "Deflate",
    "original_size": 988097824,
    "compressed_size": 771086225,
    "ratio": 1.2814362284840453,
    "comp_time": 0.46820497512817383,
    "decomp_time": 0.12714052200317383,
    "comp_speed": "1.97 GB/s",
    "decomp_speed": "7.24 GB/s"
  }
]
```
