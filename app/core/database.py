"""
Database initialization for Executor Balancer
Инициализация базы данных для системы распределения исполнителей
"""

import asyncio
import asyncpg
import redis.asyncio as redis
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def init_pool(self):
        """Инициализация пула соединений"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close_pool(self):
        """Закрытие пула соединений"""
        if self.pool:
            await self.pool.close()
            logger.info("Database pool closed")
    
    async def create_tables(self):
        """Создание таблиц базы данных"""
        if not self.pool:
            await self.init_pool()
        
        async with self.pool.acquire() as conn:
            # Таблица исполнителей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS executors (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    weight DECIMAL(3,2) DEFAULT 0.5,
                    status VARCHAR(20) DEFAULT 'active',
                    active_requests_count INTEGER DEFAULT 0,
                    success_rate DECIMAL(5,4) DEFAULT 0.0,
                    experience_years INTEGER DEFAULT 0,
                    specialization TEXT,
                    language_skills VARCHAR(100),
                    timezone VARCHAR(10) DEFAULT 'MSK',
                    daily_limit INTEGER DEFAULT 10,
                    parameters JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица заявок
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS requests (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    title VARCHAR(500) NOT NULL,
                    description TEXT NOT NULL,
                    priority VARCHAR(20) DEFAULT 'medium',
                    weight DECIMAL(3,2) DEFAULT 0.5,
                    status VARCHAR(20) DEFAULT 'pending',
                    assigned_executor_id UUID REFERENCES executors(id),
                    category VARCHAR(50) DEFAULT 'technical',
                    complexity VARCHAR(20) DEFAULT 'medium',
                    estimated_hours INTEGER DEFAULT 8,
                    required_skills TEXT[],
                    language_requirement VARCHAR(10) DEFAULT 'ru',
                    client_type VARCHAR(20) DEFAULT 'individual',
                    urgency VARCHAR(20) DEFAULT 'medium',
                    budget INTEGER,
                    technology_stack TEXT[],
                    timezone_requirement VARCHAR(20) DEFAULT 'any',
                    security_clearance VARCHAR(20) DEFAULT 'public',
                    compliance_requirements TEXT[],
                    parameters JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица назначений
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS assignments (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    request_id UUID REFERENCES requests(id),
                    executor_id UUID REFERENCES executors(id),
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'assigned',
                    completed_at TIMESTAMP,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица правил распределения
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS distribution_rules (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    priority INTEGER DEFAULT 3,
                    conditions JSONB NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица активных пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS active_users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id VARCHAR(255) NOT NULL,
                    session_id VARCHAR(255) NOT NULL,
                    ip_address INET,
                    user_agent TEXT,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Индексы для производительности
            await conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_executors_status ON executors(status);
                CREATE INDEX IF NOT EXISTS idx_executors_role ON executors(role);
                CREATE INDEX IF NOT EXISTS idx_requests_status ON requests(status);
                CREATE INDEX IF NOT EXISTS idx_requests_priority ON requests(priority);
                CREATE INDEX IF NOT EXISTS idx_assignments_executor ON assignments(executor_id);
                CREATE INDEX IF NOT EXISTS idx_assignments_request ON assignments(request_id);
                CREATE INDEX IF NOT EXISTS idx_active_users_user_id ON active_users(user_id);
                CREATE INDEX IF NOT EXISTS idx_active_users_session ON active_users(session_id);
            ''')
            
            logger.info("Database tables created successfully")

class RedisManager:
    """Менеджер Redis"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[redis.Redis] = None
    
    async def init_connection(self):
        """Инициализация соединения с Redis"""
        try:
            self.redis = redis.from_url(self.redis_url)
            await self.redis.ping()
            logger.info("Redis connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def close_connection(self):
        """Закрытие соединения с Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def set_cache(self, key: str, value: str, expire: int = 3600):
        """Установка значения в кэш"""
        if self.redis:
            await self.redis.set(key, value, ex=expire)
    
    async def get_cache(self, key: str) -> Optional[str]:
        """Получение значения из кэша"""
        if self.redis:
            return await self.redis.get(key)
        return None
    
    async def delete_cache(self, key: str):
        """Удаление значения из кэша"""
        if self.redis:
            await self.redis.delete(key)
    
    async def add_active_user(self, user_id: str, session_id: str, ip_address: str = None, user_agent: str = None):
        """Добавление активного пользователя в кэш"""
        if self.redis:
            user_data = {
                'user_id': user_id,
                'session_id': session_id,
                'ip_address': ip_address or '',
                'user_agent': user_agent or '',
                'last_activity': str(asyncio.get_event_loop().time())
            }
            await self.redis.hset(f"active_user:{session_id}", mapping=user_data)
            await self.redis.expire(f"active_user:{session_id}", 3600)  # 1 час
            await self.redis.sadd("active_users", session_id)
    
    async def remove_active_user(self, session_id: str):
        """Удаление активного пользователя из кэша"""
        if self.redis:
            await self.redis.delete(f"active_user:{session_id}")
            await self.redis.srem("active_users", session_id)
    
    async def get_active_users_count(self) -> int:
        """Получение количества активных пользователей"""
        if self.redis:
            return await self.redis.scard("active_users")
        return 0
    
    async def get_active_users(self) -> list:
        """Получение списка активных пользователей"""
        if self.redis:
            session_ids = await self.redis.smembers("active_users")
            users = []
            for session_id in session_ids:
                user_data = await self.redis.hgetall(f"active_user:{session_id}")
                if user_data:
                    users.append(user_data)
            return users
        return []

# Глобальные экземпляры
db_manager: Optional[DatabaseManager] = None
redis_manager: Optional[RedisManager] = None

async def init_database(database_url: str):
    """Инициализация базы данных"""
    global db_manager
    db_manager = DatabaseManager(database_url)
    await db_manager.init_pool()
    await db_manager.create_tables()

async def init_redis(redis_url: str):
    """Инициализация Redis"""
    global redis_manager
    redis_manager = RedisManager(redis_url)
    await redis_manager.init_connection()

async def cleanup():
    """Очистка ресурсов"""
    if db_manager:
        await db_manager.close_pool()
    if redis_manager:
        await redis_manager.close_connection()
