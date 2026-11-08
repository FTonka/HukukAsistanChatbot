# Geri getirim deneyleri

Soru dosyası: eval/questions.example.json (8 soru)

| Parçalama | Filtre | Yeniden yazım | Embedding | k | Parça | Kanun@k | Madde@k | MRR@k |
|---|---|---|---|---|---|---|---|---|
| madde | on | on | text-embedding-3-small | 5 | 577 | 88% | 62% | 0.40 |
| madde | on | on | text-embedding-3-small | 10 | 577 | 88% | 75% | 0.42 |
| madde | off | on | text-embedding-3-small | 5 | 577 | 88% | 62% | 0.40 |
| madde | off | on | text-embedding-3-small | 10 | 577 | 88% | 75% | 0.42 |
| madde:600 | on | on | text-embedding-3-small | 5 | 902 | 88% | 50% | 0.44 |
| madde:600 | on | on | text-embedding-3-small | 10 | 902 | 88% | 88% | 0.49 |
| madde:600 | off | on | text-embedding-3-small | 5 | 902 | 88% | 50% | 0.44 |
| madde:600 | off | on | text-embedding-3-small | 10 | 902 | 88% | 88% | 0.49 |
| fixed | on | on | text-embedding-3-small | 5 | 538 | 88% | 75% | 0.50 |
| fixed | on | on | text-embedding-3-small | 10 | 538 | 88% | 88% | 0.52 |
| fixed | off | on | text-embedding-3-small | 5 | 538 | 88% | 75% | 0.50 |
| fixed | off | on | text-embedding-3-small | 10 | 538 | 88% | 88% | 0.52 |
| fixed:500 | on | on | text-embedding-3-small | 5 | 1060 | 88% | 88% | 0.54 |
| fixed:500 | on | on | text-embedding-3-small | 10 | 1060 | 88% | 88% | 0.54 |
| fixed:500 | off | on | text-embedding-3-small | 5 | 1060 | 88% | 88% | 0.54 |
| fixed:500 | off | on | text-embedding-3-small | 10 | 1060 | 88% | 88% | 0.54 |
