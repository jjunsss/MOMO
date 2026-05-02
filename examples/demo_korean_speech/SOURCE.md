# Demo source

- **Title**: 발표잘하는 방법! 발표잘하는 방법 3가지
- **Uploader**: 김지혜TV리스피치
- **URL**: https://youtu.be/pYnVm6QM8fo
- **Duration**: 52 seconds
- **License**: Creative Commons Attribution (reuse allowed)
- **Upload date**: 2023-05-26

The files in this folder are MOMO's output for that clip, generated end-to-end
on a single RTX 4080 in ~70 seconds (Whisper `large-v3` + Qwen 3.5 9B + render).

Reproduce:

```bash
yt-dlp -f 'best[height<=480]/best' -o 'videos/demo.mp4' https://youtu.be/pYnVm6QM8fo
momo
```
