import os
import pandas as pd
from typing import List
from docx import Document as DocxDocument
from langchain_core.documents import Document

def read_text_file(file_path:str) -> str:
    try:
        with open(file_path,"r",encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        with open(file_path,"r",encoding="gbk") as f:
            return f.read()

def parse_docx(file_path:str) -> List[Document]:
    doc = DocxDocument(file_path)
    full_text = "\n".join([p.text for p in doc.paragraphs])
    return [Document(
        page_content = full_text,
        metadata = {"source":file_path, "type":"docx"}
    )]

def parse_txt(file_path:str) -> List[Document]:
    text = read_text_file(file_path)
    return [Document(
        page_content = text,
        metadata = {"source":file_path, "type":"txt"}
    )]

def parse_excel(file_path:str) -> List[Document]:
    """
    解析 Excel 文件，支持多 Sheet 页。
    每一行会被拼接成 "表头1: 值1, 表头2: 值2" 的格式，便于后续向量化检索。
    """
    docs = []
    xls = pd.ExcelFile(file_path)
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name)
        df = df.dropna(how="all")
        if df.empty:
            continue
        headers = df.columns.tolist()
        for index, row in df.iterrows():
            row_data = []
            for header in headers:
                val = row[header]
                if pd.notna(val):
                    row_data.append(f"{header}: {val}")
            
            if row_data:
                row_text = ", ".join(row_data)
                docs.append(Document(
                    page_content=row_text,
                    metadata={
                        "source": file_path, 
                        "type": "excel", 
                        "sheet_name": sheet_name, 
                        "row_number": index + 1  # 记录行号，方便溯源
                    }
                ))
    return docs

def parse_file_to_documents(file_path:str) -> List[Document]:
    """
    输入：文件路径
    输出：LangChain Document 列表（可直接用于 split_documents）
    """
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".txt":
        return parse_txt(file_path)
    elif ext in [".xlsx", ".xls"]:
        return parse_excel(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")
    
if __name__ == "__main__":
    test_files = [
        "../data/en_cn.docx",
        "../data/law.txt",
        "../data/test_data.xlsx", 
    ]
    for file_path in test_files:
        print("=" * 60)
        print(f"正在测试：{file_path}")
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在：{file_path}")
            continue
        try:
            docs = parse_file_to_documents(file_path)
            print(f"✅ 解析成功，共 {len(docs)} 个 Document")
            if docs:
                print("预览内容（前200字符）：")
                print(docs[0].page_content[:200].replace("\n", " "))
                print(f"元数据预览：{docs[0].metadata}")
        except Exception as e:
            print(f"❌ 解析失败：{str(e)}")
