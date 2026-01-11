# ShopGPT - AI Shopping Assistant

<div align="center">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"/>
  <img src="https://img.shields.io/badge/Google%20Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini"/>
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
</div>

## 📋 Project Overview

**ShopGPT** is an intelligent shopping assistant powered by AI that helps users discover, compare, and purchase products from major Indian e-commerce platforms. The system combines conversational AI with real-time web scraping to provide personalized product recommendations and price comparisons.

## ⚠️ Important Disclaimer

**This project is strictly for educational and learning purposes only.** It is not intended for commercial use or production deployment.

### 🚫 Production Use Restrictions
- **No Commercial Use**: This application should not be used to create commercial products or services
- **Legal Compliance**: Web scraping may violate the terms of service of e-commerce platforms
- **Rate Limiting**: The current implementation does not respect API rate limits and may result in IP blocking
- **Data Accuracy**: Scraped data may be incomplete, outdated, or inaccurate

### ✅ Recommended Production Approach
For production applications, consider partnering with official affiliate programs:
- **[Amazon Associates Program](https://affiliate-program.amazon.in/)** - Official affiliate program for Amazon.in
- **[Flipkart Affiliate Program](https://seller.flipkart.com/affiliate)** - Official partnership program for Flipkart
- **Official APIs**: Use official e-commerce APIs when available for reliable data access

### 🎓 Learning Objectives
This project demonstrates:
- AI-powered conversational interfaces
- Web scraping techniques with Playwright
- Real-time data processing and caching
- Modern web application architecture
- Integration of multiple APIs and services

### Key Features

- **🤖 AI-Powered Conversations**: Natural language chat interface using Google Gemini AI
- **🔍 Multi-Platform Search**: Simultaneous product search across Amazon and Flipkart
- **📊 Smart Comparisons**: AI-driven product analysis and recommendations
- **💰 Price Intelligence**: Automatic price filtering and budget-based suggestions
- **🎨 Modern UI**: Responsive chat interface with product cards and recommendations
- **⚡ Real-Time Scraping**: Live product data extraction using Playwright
- **💾 Session Management**: Persistent chat history and product tracking
- **🔄 Caching System**: Optimized performance with intelligent caching

## 🏗️ Architecture & How It Works

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   Django API    │    │   MCP Servers   │
│   (Chat UI)     │◄──►│   (Chat Logic)  │◄──►│   (Scrapers)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │   Google Gemini │    │   Playwright    │
│   (Sessions)    │    │   (AI Engine)   │    │   (Scraping)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### End-to-End Workflow

1. **User Interaction**: User starts a conversation through the web chat interface
2. **Intent Analysis**: Gemini AI analyzes the conversation to understand product requirements and budget
3. **Data Collection**: If sufficient details are provided, the system queries MCP servers
4. **Web Scraping**: MCP servers use Playwright to scrape real-time product data from Amazon/Flipkart
5. **AI Processing**: Gemini AI compares products and generates personalized recommendations
6. **Response Generation**: System returns formatted product cards with prices, ratings, and direct purchase links
7. **Session Persistence**: All interactions are stored in PostgreSQL for continuity

### Core Components

#### 🏠 Django Backend (`shopping_bot/`)
- **Main Application**: Handles HTTP requests and serves the chat interface
- **Chat Logic**: Processes user messages and orchestrates AI/scraping operations
- **Database Models**: Manages chat sessions and product data
- **API Endpoints**: RESTful endpoints for chat interactions and health checks

#### 🔧 MCP Servers (`mcp_server/`)
- **Amazon MCP** (`amazon_mcp.py`): FastAPI server for Amazon.in scraping
- **Flipkart MCP** (`flipkart_mcp.py`): FastAPI server for Flipkart.com scraping
- **Real-Time Scraping**: Uses Playwright for headless browser automation
- **Caching**: 5-minute cache to optimize performance and reduce load
- **Error Handling**: Fallback mechanisms for failed scrapes

#### 🎨 Frontend (`chat_app/templates/`)
- **Single-Page Application**: Modern chat interface built with HTML/CSS/JavaScript
- **Responsive Design**: Mobile-first design using Tailwind CSS
- **Real-Time Updates**: AJAX-powered message updates without page refreshes
- **Product Cards**: Interactive product display with purchase links

## 🛠️ Tech Stack

### Backend Framework
- **Django 5.2.9**: High-level Python web framework
- **Python 3.10+**: Core programming language

### AI & ML
- **Google Gemini AI**: Conversational AI and product analysis
- **Natural Language Processing**: Intent recognition and context understanding

### Web Scraping
- **Playwright**: Modern web automation framework
- **FastAPI**: High-performance async web framework for MCP servers
- **BeautifulSoup4**: HTML parsing and data extraction

### Database & Storage
- **PostgreSQL**: Primary database for session and product data
- **Redis** (optional): Caching layer for improved performance

### Frontend
- **HTML5/CSS3**: Semantic markup and modern styling
- **Tailwind CSS**: Utility-first CSS framework
- **JavaScript (ES6+)**: Client-side interactivity
- **Font Awesome**: Icon library

### Infrastructure & Tools
- **Uvicorn**: ASGI server for FastAPI applications
- **httpx**: Async HTTP client for API communications
- **python-dotenv**: Environment variable management
- **Django MCP**: Model Context Protocol integration

## 🚀 Setup Instructions

> **⚠️ Educational Use Only**: This setup is for learning purposes. See the [Disclaimer](#-important-disclaimer) section above for production use guidelines.

### Prerequisites

- **Python 3.10 or higher**
- **PostgreSQL database**
- **Google Gemini API key**
- **Node.js** (for additional frontend tooling, optional)
- **Git** for version control

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Shoppin
```

### 2. Environment Setup

#### Create Virtual Environment
```bash
python -m venv env
# On Windows:
env\Scripts\activate
# On macOS/Linux:
source env/bin/activate
```

#### Install Dependencies
```bash
pip install -r requirement.txt
```

### 3. Database Configuration

#### Install PostgreSQL
- Download and install PostgreSQL from [postgresql.org](https://www.postgresql.org/)
- Create a database named `product_bot`

#### Update Database Settings
Edit `shopping_bot/shopping_bot/settings.py`:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "product_bot",
        "USER": "postgres",  # Your PostgreSQL username
        "PASSWORD": "7010",  # Your PostgreSQL password
        "HOST": "127.0.0.1",
        "PORT": "5432",
    }
}
```

#### Run Migrations
```bash
cd shopping_bot
python manage.py makemigrations
python manage.py migrate
```

### 4. API Configuration

#### Google Gemini API
1. Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a `.env` file in the project root:
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional, for fallback
```

### 5. Run the Application

#### Start MCP Servers (in separate terminals)

**Amazon Scraper:**
```bash
cd shopping_bot/mcp_server
python amazon_mcp.py
```
Server will run on `http://localhost:8001`

**Flipkart Scraper:**
```bash
cd shopping_bot/mcp_server
python flipkart_mcp.py
```
Server will run on `http://localhost:8002`

#### Start Django Server
```bash
cd shopping_bot
python manage.py runserver
```
Application will be available at `http://localhost:8000`

### 6. Verify Installation

Visit `http://localhost:8000/health/` to check system status:
- ✅ Gemini API connection
- ✅ MCP server availability
- ✅ Database connectivity
- ✅ Model availability

## 📖 Usage Guide

### Basic Chat Interaction

1. **Start a Conversation**: Open `http://localhost:8000` in your browser
2. **Describe Your Needs**: Tell the bot what you're looking for
   - "I need a laptop under ₹50,000"
   - "Show me wireless earphones"
3. **Get Recommendations**: The bot will search and display products
4. **Compare Options**: Ask "compare all" for AI-powered analysis
5. **Make Purchases**: Click product links to buy directly

### Advanced Features

#### Price Filtering
- "laptop under 40000"
- "phone below 20000"
- "watch around 5000"

#### Platform Selection
- Default: Searches both Amazon and Flipkart
- Specify platform in advanced usage

#### Product Comparison
- Say "compare" or "which is better" after seeing products
- AI analyzes features, prices, and ratings
- Gets personalized recommendations

### API Endpoints

- `GET/POST /`: Main chat interface
- `POST /chat/`: Chat API endpoint
- `GET /health/`: System health check
- `GET /admin/`: Django admin panel

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key  # Optional fallback

# Database (if different from defaults)
DB_NAME=product_bot
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# MCP Server URLs (if different)
AMAZON_MCP_URL=http://localhost:8001
FLIPKART_MCP_URL=http://localhost:8002
```

### Django Settings

Key configuration in `settings.py`:
- `DEBUG`: Set to `False` in production
- `ALLOWED_HOSTS`: Add your domain in production
- `SECRET_KEY`: Use a strong secret key in production

## 🧪 Testing

### Health Check
Visit `/health/` endpoint to verify:
- AI model connectivity
- MCP server status
- Database connection

### Manual Testing
1. Test basic chat functionality
2. Verify product search works
3. Check comparison feature
4. Test different price ranges

## 🚀 Deployment

> **⚠️ Not for Production**: This project is designed for educational purposes only. For production deployment, use official affiliate APIs instead of web scraping.

### Production Considerations

**Note**: The following deployment guidance is for learning about deployment practices. For actual production use, integrate with official e-commerce APIs and affiliate programs.

1. **Security**:
   - Set `DEBUG=False`
   - Use environment variables for secrets
   - Configure HTTPS
   - Set up proper CORS policies

2. **Performance**:
   - Use Redis for caching
   - Set up database connection pooling
   - Configure web server (nginx/gunicorn)

3. **Monitoring**:
   - Add logging and monitoring
   - Set up error tracking
   - Monitor MCP server health

### Docker Deployment (Optional)

```dockerfile
# Example Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["python", "shopping_bot/manage.py", "runserver", "0.0.0.0:8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to functions
- Test scraping changes thoroughly
- Update documentation for API changes

## 📄 License & Usage Terms

This project is licensed under the MIT License - see the LICENSE file for details.

### ⚖️ Usage Terms
- **Educational Use Only**: This codebase is provided solely for learning and educational purposes
- **No Commercial Use**: Do not use this code to create commercial products or services
- **Legal Compliance**: Users are responsible for complying with the terms of service of scraped websites
- **Ethical Use**: Respect website policies and implement proper rate limiting in any derivative works

### 🔗 Production Alternatives
For commercial applications, please use official APIs and affiliate programs:
- [Amazon Associates Program](https://affiliate-program.amazon.in/)
- [Flipkart Affiliate Program](https://seller.flipkart.com/affiliate)
- Official e-commerce platform APIs

## 🙏 Acknowledgments

- **Google Gemini AI** for powering the conversational interface
- **Playwright** for reliable web scraping capabilities
- **FastAPI** for high-performance MCP server implementation
- **Django** for the robust web framework foundation

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the health endpoint for system status
- Review logs for debugging information

---

<div align="center">
  <p><strong>Built with ❤️ using Django, Gemini AI, and modern web technologies</strong></p>
  <p>Making shopping smarter, one conversation at a time.</p>
</div>    
