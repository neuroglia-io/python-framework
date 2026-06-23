# MongoDB Express Access Guide

## 🔐 How to Access MongoDB Express

MongoDB Express is the web-based admin UI for MongoDB in the Mario's Pizzeria stack.

### 📍 Access Information

- **URL**: http://localhost:8081
- **Authentication**: **DISABLED** (for development convenience)
- **Direct Access**: No login required!

### � Quick Access

Simply open your browser and navigate to:

```
http://localhost:8081
```

**No username or password needed!** You'll immediately see the MongoDB databases.

### ⚠️ Important Security Note

**DEVELOPMENT ONLY**: Basic authentication has been disabled for local development convenience.

**Never deploy this configuration to production!** In production:

- Enable basic authentication (`ME_CONFIG_BASICAUTH: "true"`)
- Use strong passwords
- Restrict network access
- Enable TLS/SSL
- Use proper authentication mechanisms

### 🗄️ MongoDB Connection Details

Once logged in, you'll have access to:

- **Server**: `mongodb` (internal Docker network name)
- **Port**: `27017`
- **Admin User**: `root`
- **Admin Password**: `mario123`
- **Default Database**: `mario_pizzeria`

### 📊 What You Can Do

- **Browse databases**: See all databases in the MongoDB instance
- **View collections**: Explore collections like `orders`, `menu_items`, `customers`
- **Query data**: Run queries directly in the web interface
- **Edit documents**: Modify data through the UI
- **Create/Delete**: Manage databases and collections
- **Import/Export**: Transfer data in/out of MongoDB

### 🔧 Troubleshooting

#### Issue: Page Not Loading

**Check if MongoDB is running**:

```bash
docker-compose -f docker-compose.mario.yml ps mongodb
```

**Check MongoDB Express logs**:

```bash
docker-compose -f docker-compose.mario.yml logs mongo-express
```

**Look for**: `Server is open to allow connections from anyone (0.0.0.0)`

**Restart both services**:

```bash
docker-compose -f docker-compose.mario.yml restart mongodb mongo-express
```

#### Issue: Cannot See Databases

**Check MongoDB connection**:

```bash
docker-compose -f docker-compose.mario.yml logs mongodb
```

**Verify MongoDB is accessible**:

```bash
docker-compose -f docker-compose.mario.yml exec mongodb mongosh --eval "db.adminCommand('listDatabases')"
```

### 🎯 Quick Access Commands

```bash
# Open in default browser (macOS)
open http://localhost:8081

# Open in default browser (Linux)
xdg-open http://localhost:8081

# Open in default browser (Windows)
start http://localhost:8081
```

### 🔒 Security Notes

**⚠️ Development Only**: These credentials are for local development only.

**Never use in production**:

- Change default passwords
- Use proper authentication mechanisms
- Restrict network access
- Enable TLS/SSL
- Use environment variables for secrets

### 📚 Common Queries

Once logged in, here are some useful MongoDB queries you can run:

**View all orders**:

```javascript
db.orders.find();
```

**Find orders by status**:

```javascript
db.orders.find({ status: "PENDING" });
```

**Count total orders**:

```javascript
db.orders.count();
```

**View menu items**:

```javascript
db.menu_items.find();
```

**Find pizzas by name**:

```javascript
db.menu_items.find({ name: /Margherita/i });
```

## ✅ Verification Checklist

- [ ] Can access http://localhost:8081
- [ ] No authentication prompt appears
- [ ] Can see MongoDB databases immediately
- [ ] Can browse `mario_pizzeria` database
- [ ] Can view collections (orders, menu_items, etc.)
- [ ] Can query and view documents

## 🆘 Still Having Issues?

If you're still getting "Unauthorized":

1. **Clear all browser data** for localhost:8081
2. **Try a different browser** (Chrome, Firefox, Safari)
3. **Use curl to test**:

   ```bash
   curl -u admin:admin123 http://localhost:8081
   ```

4. **Check Docker logs** for any error messages
5. **Restart the entire stack**:

   ```bash
   docker-compose -f docker-compose.mario.yml down
   docker-compose -f docker-compose.mario.yml up -d
   ```
