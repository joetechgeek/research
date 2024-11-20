from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_community.chains import RetrievalQAWithSourcesChain
from langchain_core.documents import Document
from typing import List, Optional
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleEmbeddings:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=512)
        self.fitted = False
    
    def embed_documents(self, texts: List[str]) -> List[np.ndarray]:
        if not self.fitted:
            vectors = self.vectorizer.fit_transform(texts).toarray()
            self.fitted = True
        else:
            vectors = self.vectorizer.transform(texts).toarray()
        return vectors.tolist()
    
    def embed_query(self, text: str) -> List[float]:
        if not self.fitted:
            raise ValueError("Embeddings must be fitted with documents first")
        return self.vectorizer.transform([text]).toarray()[0].tolist()

class WebScraper:
    def __init__(self):
        self.embeddings = SimpleEmbeddings()
        
    def scrape_urls(self, urls: List[str]) -> List[Document]:
        documents = []
        for url in urls:
            try:
                logger.info(f"Scraping URL: {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                
                if not text:
                    logger.warning(f"No text content found for URL: {url}")
                    continue
                    
                documents.append(Document(
                    page_content=text,
                    metadata={"source": url}
                ))
                
                # Be nice to servers
                time.sleep(1)
                
            except requests.RequestException as e:
                logger.error(f"Error scraping {url}: {str(e)}")
                continue
                
        if not documents:
            logger.error("No documents were successfully scraped")
            return []
            
        return documents
        
    def create_vector_store(self, documents: List[Document]) -> Optional[FAISS]:
        try:
            logger.info("Creating vector store...")
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            texts = text_splitter.split_documents(documents)
            
            if not texts:
                logger.error("No texts after splitting documents")
                return None
                
            vector_store = FAISS.from_documents(texts, self.embeddings)
            logger.info("Vector store created successfully")
            return vector_store
            
        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            return None
            
    def setup_qa_chain(self, vector_store: FAISS) -> Optional[RetrievalQAWithSourcesChain]:
        try:
            logger.info("Setting up QA chain...")
            prompt_template = """Use the following pieces of context to answer the question at the end. 
            If you don't know the answer, just say that you don't know, don't try to make up an answer.

            {context}

            Question: {question}
            Answer:"""
            
            PROMPT = PromptTemplate(
                template=prompt_template, input_variables=["context", "question"]
            )
            
            chain = RetrievalQAWithSourcesChain.from_chain_type(
                llm=None,  # We'll need to add an LLM here
                chain_type="stuff",
                retriever=vector_store.as_retriever(),
                return_source_documents=True,
                chain_type_kwargs={"prompt": PROMPT}
            )
            
            logger.info("QA chain setup completed")
            return chain
            
        except Exception as e:
            logger.error(f"Error setting up QA chain: {str(e)}")
            return None