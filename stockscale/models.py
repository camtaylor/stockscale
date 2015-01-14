from google.appengine.ext import db


class Stock(db.Model):
  """Model of a stock, owner property for its associated user"""
  owner = db.StringProperty()
  symbol = db.StringProperty()
  price = db.FloatProperty()
  shares = db.IntegerProperty()
  company_name = db.StringProperty()
  purchase_price = db.FloatProperty()
  change = db.FloatProperty()

class User(db.Model):
  """user entity contains balances an a unique id, user_key"""
  user_key = db.StringProperty()
  name = db.StringProperty()
  cash_balance = db.FloatProperty()
  assets_balance = db.FloatProperty()
  asset_change = db.FloatProperty()

