# Contributing to Gemini Trader

Thank you for your interest in contributing to Gemini Trader! This document provides guidelines and instructions for contributing to the project.

## 🤝 How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Detailed steps to reproduce the bug
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)
- Relevant logs or error messages

### Suggesting Enhancements

Enhancement suggestions are welcome! Please create an issue with:
- A clear, descriptive title
- Detailed description of the proposed feature
- Why this enhancement would be useful
- Any relevant examples or mockups

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines below
3. **Test your changes** thoroughly
4. **Update documentation** if needed
5. **Commit your changes** with clear, descriptive commit messages
6. **Push to your fork** and submit a pull request

## 💻 Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/gemini-trader.git
cd gemini-trader
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your test credentials (use testnet/demo accounts)

5. Set up a test database:
```bash
# Create a test database
createdb gemini_trader_test
# Update your .env with test database URL
```

## 📝 Code Style Guidelines

### Python Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and concise
- Comment complex logic

Example:
```python
def calculate_position_size(account_balance: float, risk_percentage: float) -> float:
    """
    Calculate the position size based on account balance and risk percentage.
    
    Args:
        account_balance: Total account balance in USD
        risk_percentage: Percentage of account to risk (e.g., 0.02 for 2%)
    
    Returns:
        Position size in USD
    """
    return account_balance * risk_percentage
```

### Commit Message Guidelines

- Use clear, descriptive commit messages
- Start with a verb in present tense (Add, Fix, Update, Remove, etc.)
- Keep the first line under 50 characters
- Add detailed description if needed after a blank line

Good examples:
```
Add stop-loss validation for spot trades
Fix RSI calculation for edge cases
Update documentation for API endpoints
```

### Testing Guidelines

Before submitting a pull request:

1. **Test with Demo/Testnet**: Always test with Bybit demo or testnet accounts
2. **Test Both Modes**: If applicable, test both spot and perpetual modes
3. **Check Edge Cases**: Test with various market conditions
4. **Verify Database Changes**: Ensure database operations work correctly
5. **Check Logs**: Review logs for any warnings or errors

## 🔍 Code Review Process

1. Maintainers will review your pull request
2. They may request changes or ask questions
3. Make requested changes and push to your branch
4. Once approved, your PR will be merged

## 🎯 Areas for Contribution

Here are some areas where contributions would be especially valuable:

### High Priority
- **Testing Framework**: Add unit tests and integration tests
- **Backtesting Module**: Historical strategy testing
- **Risk Management**: Enhanced risk calculation and position sizing
- **Error Handling**: More robust error handling and recovery
- **Performance Optimization**: Improve execution speed

### Medium Priority
- **Additional Exchanges**: Support for other exchanges (Binance, OKX, etc.)
- **More Strategies**: Additional trading strategies and indicators
- **Web Dashboard**: Web-based monitoring and control interface
- **Notification System**: Alerts via Telegram, Discord, email, etc.
- **Multi-Symbol Trading**: Support for trading multiple symbols simultaneously

### Documentation
- **API Documentation**: More detailed API endpoint documentation
- **Strategy Guides**: Detailed strategy explanation and tuning guides
- **Video Tutorials**: Setup and usage video tutorials
- **Troubleshooting Guide**: Common issues and solutions

## 🛡️ Security

- **Never commit API keys or secrets** to the repository
- **Use environment variables** for all sensitive data
- **Test with demo accounts** before suggesting live trading features
- **Report security vulnerabilities** privately to the maintainers

## 📜 Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## ❓ Questions?

If you have questions about contributing:
- Open an issue with the "question" label
- Check existing issues for similar questions
- Review the documentation thoroughly first

## 🙏 Thank You!

Your contributions make this project better for everyone. Thank you for taking the time to contribute!
