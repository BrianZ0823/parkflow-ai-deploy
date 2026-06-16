# -*- coding: utf-8 -*-
"""
ChromaDB向量知识库 - 使用 ChromaDB + 阿里百炼 text-embedding-v3
支持 Python 3.10+
"""
import os
import sys
from typing import List, Dict, Any

# 禁用 ChromaDB 遥测
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_CLIENT_AUTH_PROVIDER"] = "chromadb.auth.impl.basic.BasicAuthClientProvider"
# 限制 Numpy/OpenBLAS/MKL 线程数，防止 subprocess 挂起
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

# 临时重定向 stdout 到 stderr，防止 chromadb 打印各种 banner 破坏 MCP 协议
old_stdout = sys.stdout
try:
    sys.stdout = sys.stderr
    import chromadb
    from chromadb.config import Settings
    from openai import OpenAI
finally:
    sys.stdout = old_stdout

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ChromaDB存储路径
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, "db", "chromadb")

# 全局实例缓存（单例模式）
_VECTOR_STORE_INSTANCE = None


def get_vector_store():
    """获取或创建 ChromaDB 向量存储实例（单例模式）"""
    global _VECTOR_STORE_INSTANCE
    if _VECTOR_STORE_INSTANCE is None:
        _VECTOR_STORE_INSTANCE = ChromaVectorStore()
    return _VECTOR_STORE_INSTANCE


def reset_vector_store():
    """重置向量存储实例（用于释放资源）"""
    global _VECTOR_STORE_INSTANCE
    if _VECTOR_STORE_INSTANCE:
        # 尝试显式删除 client 以触发析构（释放文件句柄）
        try:
            del _VECTOR_STORE_INSTANCE.client
        except AttributeError:
            pass
        _VECTOR_STORE_INSTANCE = None
        import gc
        gc.collect()
        print("[ChromaDB] 向量存储实例已重置", file=sys.stderr)


class ChromaVectorStore:
    """ChromaDB向量存储：使用阿里百炼 Embeddings"""

    def __init__(self):
        # 读取API Key
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            key_file = os.path.join(PROJECT_ROOT, "api_key.txt")
            if os.path.exists(key_file):
                with open(key_file, 'r', encoding='utf-8') as f:
                    api_key = f.read().strip()
        
        if not api_key:
            raise ValueError("未找到 DASHSCOPE_API_KEY，请设置环境变量或在 api_key.txt 中填入 API Key")
        
        # 初始化 OpenAI 客户端（用于生成嵌入向量）
        self.embedding_client = OpenAI(
            api_key=api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            max_retries=int(os.getenv("EMBEDDING_MAX_RETRIES", "2")),
            timeout=30.0  # 设置30秒超时，避免无限等待
        )
        
        # 初始化 ChromaDB 客户端
        os.makedirs(CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=CHROMA_DB_PATH,
            settings=Settings(anonymized_telemetry=False)
        )
        
        print(f"[ChromaDB] 初始化成功，存储路径: {CHROMA_DB_PATH}", file=sys.stderr)

    def _get_embedding(self, text: str) -> List[float]:
        """使用阿里百炼生成嵌入向量"""
        try:
            print(f"[ChromaDB] 正在请求 Embedding API (length={len(text)})...", file=sys.stderr)
            response = self.embedding_client.embeddings.create(
                model="text-embedding-v3",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[ChromaDB] 生成嵌入向量失败: {e}", file=sys.stderr)
            raise

    def _get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        try:
            print(f"[ChromaDB] 正在批量请求 Embedding API (count={len(texts)})...", file=sys.stderr)
            response = self.embedding_client.embeddings.create(
                model="text-embedding-v3",
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"[ChromaDB] 批量生成嵌入向量失败: {e}", file=sys.stderr)
            raise

    def get_or_create_collection(self, name: str):
        """获取或创建 Collection"""
        try:
            collection = self.client.get_collection(name=name)
            print(f"[ChromaDB] 已获取现有 Collection: {name}", file=sys.stderr)
        except chromadb.errors.NotFoundError:
            # Collection 不存在，创建新的
            collection = self.client.create_collection(
                name=name,
                metadata={"description": f"Collection for {name}"}
            )
            print(f"[ChromaDB] 已创建新 Collection: {name}", file=sys.stderr)
        return collection

    def add_collection(self, name: str, docs: List[dict]):
        """添加一个集合的文档
        
        Args:
            name: Collection 名称
            docs: 文档列表,每个文档包含 {"id", "content", ...其他元数据}
        """
        collection = self.get_or_create_collection(name)
        
        # 提取内容和元数据
        ids = [doc["id"] for doc in docs]
        contents = [doc["content"] for doc in docs]
        metadatas = []
        for doc in docs:
            metadata = {k: str(v) for k, v in doc.items() if k not in ("id", "content")}
            # ChromaDB要求metadata必须是非空字典或None
            metadatas.append(metadata if metadata else None)
        
        # 批量生成嵌入向量
        print(f"[ChromaDB] 正在为 {len(docs)} 个文档生成嵌入向量...", file=sys.stderr)
        embeddings = self._get_embeddings_batch(contents)
        
        # 添加到 Collection
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=contents,
            metadatas=metadatas
        )
        
        print(f"[ChromaDB] Collection '{name}' 已添加 {len(docs)} 个文档", file=sys.stderr)

    def query(self, query: str, collection: str = "all", top_k: int = 3) -> List[Dict[str, Any]]:
        """语义检索
        
        Args:
            query: 查询文本
            collection: Collection名称，"all"表示搜索所有集合
            top_k: 返回结果数量
        
        Returns:
            检索结果列表
        """
        # 生成查询向量
        query_embedding = self._get_embedding(query)
        
        results = []
        
        if collection == "all":
            # 搜索所有 Collection
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]
        else:
            collection_names = [collection]
        
        # 从每个 Collection 中检索
        for col_name in collection_names:
            try:
                col = self.client.get_collection(name=col_name)
                query_result = col.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k
                )
                
                # 格式化结果
                if query_result['ids'] and len(query_result['ids'][0]) > 0:
                    for i in range(len(query_result['ids'][0])):
                        results.append({
                            "id": query_result['ids'][0][i],
                            "collection": col_name,
                            "content": query_result['documents'][0][i],
                            "metadata": query_result['metadatas'][0][i],
                            "similarity": 1 - query_result['distances'][0][i],  # 转换为相似度
                        })
            except Exception as e:
                print(f"[ChromaDB] 查询 Collection '{col_name}' 失败: {e}", file=sys.stderr)
        
        # 按相似度排序并返回 top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def delete_collection(self, name: str):
        """删除 Collection"""
        try:
            self.client.delete_collection(name=name)
            print(f"[ChromaDB] 已删除 Collection: {name}", file=sys.stderr)
        except Exception as e:
            print(f"[ChromaDB] 删除 Collection 失败: {e}", file=sys.stderr)

    def list_collections(self) -> List[str]:
        """列出所有 Collection"""
        collections = self.client.list_collections()
        return [col.name for col in collections]


def init_vector_store():
    """初始化向量知识库"""
    from data.seed_data.knowledge_docs import (
        COMPANY_PROFILES, PARK_BROCHURES, INDUSTRY_REPORTS, POLICY_SUMMARIES,
    )

    print("=" * 60)  # 这里保留 stdout，因其是单独的初始化脚本，不是 MCP 服务
    print("初始化 ChromaDB 向量知识库")
    print("=" * 60)

    store = get_vector_store()  # 使用单例模式
    
    # Data Collections
    collections_data = {
        "company_profiles": COMPANY_PROFILES,
        "park_brochures": PARK_BROCHURES,
        "industry_reports": INDUSTRY_REPORTS,
        "policy_summaries": POLICY_SUMMARIES,
    }

    # Reset: Delete existing collections first
    print("\n[VectorStore]正在重置数据库（删除旧集合）...")
    existing_collections = store.list_collections()
    for name in collections_data.keys():
        if name in existing_collections:
            store.delete_collection(name)

    # Add collections
    for name, docs in collections_data.items():
        print(f"\n[VectorStore] 正在处理集合 '{name}' ({len(docs)} 条)...")
        store.add_collection(name, docs)

    print("\n" + "=" * 60)
    print("向量库初始化完成！")
    print(f"存储位置: {CHROMA_DB_PATH}")
    print(f"Collections: {', '.join(store.list_collections())}")
    print("=" * 60)

    # 测试查询
    print("\n测试查询...")
    test_query = "企业入驻需要什么材料？"
    results = store.query(test_query, top_k=2)
    print(f"\n查询: {test_query}")
    for i, result in enumerate(results, 1):
        title = result['metadata'].get('title', 'N/A') if result['metadata'] else 'N/A'
        print(f"  [{i}] {title} (相似度: {result['similarity']:.4f})")
        print(f"      {result['content'][:100]}...")
    
    # 清理可能生成的空白文件夹
    _cleanup_empty_dirs(CHROMA_DB_PATH)


def _cleanup_empty_dirs(path):
    """递归删除空目录"""
    if not os.path.isdir(path):
        return

    # 先遍历子目录
    for d in os.listdir(path):
        full_path = os.path.join(path, d)
        if os.path.isdir(full_path):
            _cleanup_empty_dirs(full_path)
    
    # 再次检查当前目录是否为空（如果子目录被删除，当前目录可能变为空）
    # 注意：不要删除根数据库目录本身，只删除子文件夹
    if path != CHROMA_DB_PATH:
        try:
            if not os.listdir(path):
                os.rmdir(path)
                print(f"[Cleanup] 已删除空目录: {path}", file=sys.stderr)
        except OSError:
            pass


if __name__ == "__main__":
    init_vector_store()
