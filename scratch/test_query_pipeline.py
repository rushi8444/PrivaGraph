import os
import io
os.environ["PYTHONIOENCODING"] = "utf-8"
import asyncio
from app.api.dependencies import get_state, get_default_user
from app.retrieval.synthesizer import AnswerSynthesizer
from app.ingestion.schema_registry import validate_entity_categories

async def main():
    state = get_state()
    user = get_default_user()

    pdf_path = "tests/fixtures/doc1_hr_compensation.pdf"
    with open(pdf_path, "rb") as f:
        content = f.read()

    doc = state.pdf_converter.convert(
        content=content,
        filename="doc1_hr_compensation.pdf",
    )
    doc_id = doc.header.document.id
    detector = state.get_detector()
    entity_categories = validate_entity_categories(doc.header.privacy.entity_categories)

    tokenized_sentences = []
    for sentence in doc.sentences:
        entities = detector.detect(
            text=sentence,
            entity_categories=entity_categories,
            min_confidence=doc.header.privacy.min_confidence,
        )
        tokenized_text, tok_entities = state.tokenizer.tokenize_text(sentence, entities)
        tokenized_sentences.append(tokenized_text)
        for tok in tok_entities:
            await state.vault.store(
                token=tok.token,
                entity_type=tok.entity_type,
                original_value=tok.original_value,
                hmac_digest=tok.hmac_digest,
                doc_id=doc_id,
            )

    all_triples = []
    prev_subject = None
    for sentence in tokenized_sentences:
        triples = state.triple_extractor.extract(sentence, doc_id=doc_id, prev_subject=prev_subject)
        all_triples.extend(triples)
        if triples:
            prev_subject = triples[0].subject
    state.graph_builder.add_triples(all_triples, doc.header)

    # Test query
    query = "What is Priya Nandakumar's Social Security Number?"
    q_entities = detector.detect(query)
    tok_query, q_tokens = state.tokenizer.tokenize_text(query, q_entities)
    for tok in q_tokens:
        await state.vault.store(
            token=tok.token,
            entity_type=tok.entity_type,
            original_value=tok.original_value,
            hmac_digest=tok.hmac_digest,
            doc_id="query",
        )

    context = state.context_builder.build_context(
        query=tok_query if q_entities else query,
        user=user,
    )

    print("--- CONTEXT ---")
    print(context)
    print("--- TOK QUERY ---")
    print(tok_query)

    synth = AnswerSynthesizer()
    res_raw = synth.synthesize(tok_query, context)
    print("--- SYNTHESIZED RAW ---")
    print(res_raw)

    recon, _ = await state.reconstructor.reconstruct(res_raw)
    print("--- RECONSTRUCTED ---")
    print(recon)

asyncio.run(main())
