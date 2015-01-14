import cgi
import os
import urllib
import webapp2
import logging
from google.appengine.api import taskqueue
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from time import time
from google.appengine.ext import deferred
from google.appengine.api import users
import ystockquote

class Stock(db.Model):
  owner = db.StringProperty()
  symbol = db.StringProperty()
  price = db.FloatProperty()
  shares = db.IntegerProperty()
  company_name = db.StringProperty()
  purchase_price = db.FloatProperty()
  change = db.FloatProperty()

class User(db.Model):
  user_key = db.StringProperty()
  name = db.StringProperty()
  cash_balance = db.FloatProperty()
  assets_balance = db.FloatProperty()
 
class StockHandler(webapp2.RequestHandler):
  def get(self):

    user = users.get_current_user()
    if user:
      registered_account = User.all().filter('user_key =', user.user_id()).count()
      if registered_account > 0:
        logout = users.create_logout_url('/')
        q = Stock.all().filter('owner =', user.user_id())
        u = User.all().filter('user_key =', user.user_id()).get()
        self.response.out.write(template.render('main.html',
                                                {'stocks': q, 'user':u, 'logout':logout}))
      else:
        def create_account():
          user = users.get_current_user()
          account = User(key_name=user.user_id())
          account.user_key= user.user_id()
          account.name = user.nickname()
          account.cash_balance = 100000.0
          account.assets_balance = 0.0
          account.put()
        create_account()
        self.redirect('/')
    else:
      self.redirect(users.create_login_url(self.request.uri))


class NewStock(webapp2.RequestHandler):
  def post(self):
    user = users.get_current_user()
    trade_account = User.all().filter('user_key =', user.user_id()).get()
    ticker = cgi.escape(self.request.get('stock')).upper()
    shares = float(self.request.get('shares'))
    latest_price = float(ystockquote.get_last_trade_price(ticker))
    trade_cost = shares * latest_price
    
    if trade_cost < trade_account.cash_balance:
      xg_on = db.create_transaction_options(xg=True)
      def buy_stock():
        #invalid ticker symbols return 0, check for valid symbol
        if latest_price > 0:
          name = ystockquote.get_company_name(ticker)
          new_stock = Stock()
          new_stock.symbol = ticker
          new_stock.price = latest_price
          new_stock.shares = int(shares)
          new_stock.purchase_price = latest_price
          new_stock.company_name = name
          new_stock.change = 0.0
          user = users.get_current_user()
          if user:
            new_stock.owner = user.user_id()
            new_stock.put()
          trade_account.cash_balance -= trade_cost
          trade_account.assets_balance += trade_cost
          trade_account.put()
      db.run_in_transaction_options(xg_on, buy_stock)
    self.redirect('/')


class UpdatePrices(webapp2.RequestHandler):
  def post(self):
    user_id = users.get_current_user().user_id()
    stocks = Stock.all().filter('owner =', user_id)
    total = 0.0
    if stocks.count() != 0:
      for stock in stocks:
        stock.price = float(ystockquote.get_last_trade_price(stock.symbol))
        stock.change = stock.price - stock.purchase_price
        total += stock.price * stock.shares
        stock.put()
    account = User.all().filter('user_key =', user_id).get()
    account.assets_balance = total
    account.put()
    self.redirect('/')

class SellStock(webapp2.RequestHandler):
  def post(self):
    user = users.get_current_user()
    trade_account = User.all().filter('user_key =', user.user_id()).get()
    ticker = cgi.escape(self.request.get('stock'))
    shares = float(self.request.get('shares'))
    latest_price = float(ystockquote.get_last_trade_price(ticker))
    trade_cost = shares * latest_price
    stocks = Stock.all().filter('owner =', user.user_id())

    def sell_stock(symbol, portfolio, shares_to_sell, user):
      stocks_to_sell = portfolio.filter('symbol =', symbol)
      total = 0.0
      for stock in stocks_to_sell:
        total += stock.price * stock.shares
        stock.delete()
      user.cash_balance += total
      user.assets_balance -= total
      user.put()
    sell_stock(ticker, stocks, shares_to_sell, trade_account)
    self.redirect('/')

app = webapp2.WSGIApplication([
    ('/', StockHandler),
    ('/addstock', NewStock),
    ('/updateprices', UpdatePrices),
    ('/sellstock', SellStock)
], debug=True)
