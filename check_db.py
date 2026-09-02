import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import chromadb

client = chromadb.PersistentClient(path='data/chroma_db')
col = client.get_collection('groww_funds')

large_cap_docs = col.get(where={'fund_category': 'Large Cap'})
print('Total Large Cap chunks:', len(large_cap_docs['ids']))

for i, d in enumerate(large_cap_docs['documents']):
    if '1.02%' in d:
        print(f'Found target chunk! ID: {large_cap_docs["ids"][i]}')
        print(f'Text preview: {d[:150].encode("ascii", "replace").decode("ascii")}')
