from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库连接
DATABASE_URL = "mysql+pymysql://root:data1234@sh-cdb-nncpvxj4.sql.tencentcdb.com:27709/my_db?charset=utf8mb4"
engine = create_engine(DATABASE_URL)
Base = declarative_base()
print("Database connected successfully.")

print("Creating database tables...")

# 定义 TxtFile 表
class TxtFile(Base):
    __tablename__ = 'txt_files'
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_content = Column(Text, nullable=False)
    upload_time = Column(TIMESTAMP, server_default=func.now())

# 定义 UsageStats 表
class UsageStats(Base):
    __tablename__ = 'usage_stats'
    id = Column(Integer, primary_key=True, autoincrement=True)
    feature = Column(String(255), nullable=False)
    count = Column(Integer, nullable=False, default=0)

# 创建所有表
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

print("Database tables created successfully.")