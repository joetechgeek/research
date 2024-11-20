import requests
from bs4 import BeautifulSoup
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA, LLMChain
from langchain_community.llms import HuggingFaceHub
from langchain.prompts import PromptTemplate

class WebScraper:
    def __init__(self):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        self.embeddings = HuggingFaceEmbeddings()

    def scrape_urls(self, urls):
        documents = []
        for url in urls:
            try:
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text and clean it
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                
                # Split text into chunks
                texts = self.text_splitter.split_text(text)
                documents.extend(texts)
                
            except Exception as e:
                print(f"Error scraping {url}: {str(e)}")
                continue
                
        return documents

    def create_vector_store(self, documents):
        try:
            vector_store = FAISS.from_texts(
                documents,
                self.embeddings
            )
            return vector_store
        except Exception as e:
            print(f"Error creating vector store: {str(e)}")
            return None

    def setup_qa_chain(self, vector_store):
        try:
            # Initialize retriever
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # Create custom prompt
            template = """<s>[INST] Use the following pieces of context to answer the question at the end. 
            If you don't know the answer, just say that you don't know, don't try to make up an answer.
            
            Context: {context}
            
            Question: {question} [/INST]
            
            Answer: """
            
            QA_CHAIN_PROMPT = PromptTemplate(
                input_variables=["context", "question"],
                template=template,
            )

            # Initialize Llama model using HuggingFace Hub
            llm = HuggingFaceHub(
                repo_id="meta-llama/Llama-3.2-3B-Instruct",
                model_kwargs={
                    "temperature": 0.7,
                    "max_new_tokens": 2048,
                    "top_p": 0.9,
                }
            )

            # Initialize QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": QA_CHAIN_PROMPT}
            )
            
            return qa_chain
            
        except Exception as e:
            print(f"Error setting up QA chain: {str(e)}")
            return None