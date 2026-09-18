from app.api.dependencies import get_state

s = get_state()
d = s.get_detector()
query = "What is Priya Nandakumar's Social Security Number?"
res = d.detect(query)
print("Use presidio:", getattr(d, 'use_presidio', None))
print("Detected:", [(r.entity_type, r.original_value) for r in res])

tok_text, entities = s.tokenizer.tokenize_text(query, res)
print("Tokenized text:", tok_text)
