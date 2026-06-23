// MongoDB initialization script for Mario's Pizzeria
// This script creates the initial database and collections with proper indexes

print('🍕 Initializing Mario\'s Pizzeria Database...');

// Switch to the mario_pizzeria database
db = db.getSiblingDB('mario_pizzeria');

// Create collections with validation schemas
db.createCollection('customers', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['id', 'email'],
            properties: {
                id: { bsonType: 'string' },
                email: { bsonType: 'string', pattern: '^.+@.+\..+$' },
                state: {
                    bsonType: 'object',
                    required: ['id', 'email'],
                    properties: {
                        id: { bsonType: 'string' },
                        name: { bsonType: ['string', 'null'] },
                        email: { bsonType: 'string' },
                        phone: { bsonType: 'string' },
                        address: { bsonType: 'string' },
                        user_id: { bsonType: ['string', 'null'] }
                    }
                },
                version: { bsonType: 'int' }
            }
        }
    }
});

db.createCollection('pizzas', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['_id', 'name', 'basePrice', 'ingredients'],
            properties: {
                _id: { bsonType: 'string' },
                name: { bsonType: 'string', minLength: 1 },
                description: { bsonType: 'string' },
                basePrice: { bsonType: 'double', minimum: 0 },
                category: { bsonType: 'string', enum: ['classic', 'premium', 'vegetarian', 'vegan', 'special'] },
                ingredients: {
                    bsonType: 'array',
                    items: { bsonType: 'string' }
                },
                allergens: {
                    bsonType: 'array',
                    items: { bsonType: 'string' }
                },
                isAvailable: { bsonType: 'bool' },
                preparationTimeMinutes: { bsonType: 'int', minimum: 1 },
                createdAt: { bsonType: 'date' },
                updatedAt: { bsonType: 'date' }
            }
        }
    }
});

db.createCollection('orders', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['_id', 'customerId', 'items', 'totalAmount', 'status'],
            properties: {
                _id: { bsonType: 'string' },
                customerId: { bsonType: 'string' },
                items: {
                    bsonType: 'array',
                    items: {
                        bsonType: 'object',
                        required: ['pizzaId', 'quantity', 'unitPrice'],
                        properties: {
                            pizzaId: { bsonType: 'string' },
                            quantity: { bsonType: 'int', minimum: 1 },
                            unitPrice: { bsonType: 'double', minimum: 0 },
                            customizations: {
                                bsonType: 'array',
                                items: { bsonType: 'string' }
                            }
                        }
                    }
                },
                totalAmount: { bsonType: 'double', minimum: 0 },
                status: { bsonType: 'string', enum: ['pending', 'confirmed', 'preparing', 'ready', 'delivered', 'cancelled'] },
                orderType: { bsonType: 'string', enum: ['dine-in', 'takeaway', 'delivery'] },
                estimatedDeliveryTime: { bsonType: 'date' },
                deliveryAddress: {
                    bsonType: 'object',
                    properties: {
                        street: { bsonType: 'string' },
                        city: { bsonType: 'string' },
                        zipCode: { bsonType: 'string' },
                        instructions: { bsonType: 'string' }
                    }
                },
                paymentStatus: { bsonType: 'string', enum: ['pending', 'paid', 'failed', 'refunded'] },
                createdAt: { bsonType: 'date' },
                updatedAt: { bsonType: 'date' }
            }
        }
    }
});

db.createCollection('kitchen_queue', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['_id', 'orderId', 'status', 'priority'],
            properties: {
                _id: { bsonType: 'string' },
                orderId: { bsonType: 'string' },
                status: { bsonType: 'string', enum: ['queued', 'preparing', 'ready', 'served'] },
                priority: { bsonType: 'int', minimum: 1, maximum: 10 },
                assignedChef: { bsonType: 'string' },
                estimatedCompletionTime: { bsonType: 'date' },
                actualStartTime: { bsonType: 'date' },
                actualCompletionTime: { bsonType: 'date' },
                notes: { bsonType: 'string' },
                createdAt: { bsonType: 'date' },
                updatedAt: { bsonType: 'date' }
            }
        }
    }
});

// Create indexes for better performance
print('📊 Creating database indexes...');

// Customer indexes
db.customers.createIndex({ email: 1 }, { unique: true });
db.customers.createIndex({ phone: 1 });
db.customers.createIndex({ createdAt: 1 });
db.customers.createIndex({ isActive: 1 });

// Pizza indexes
db.pizzas.createIndex({ name: 1 });
db.pizzas.createIndex({ category: 1 });
db.pizzas.createIndex({ isAvailable: 1 });
db.pizzas.createIndex({ basePrice: 1 });

// Order indexes
db.orders.createIndex({ customerId: 1 });
db.orders.createIndex({ status: 1 });
db.orders.createIndex({ createdAt: 1 });
db.orders.createIndex({ paymentStatus: 1 });
db.orders.createIndex({ orderType: 1 });
db.orders.createIndex({ 'customerId': 1, 'createdAt': -1 });

// Kitchen queue indexes
db.kitchen_queue.createIndex({ orderId: 1 }, { unique: true });
db.kitchen_queue.createIndex({ status: 1 });
db.kitchen_queue.createIndex({ priority: -1, createdAt: 1 });
db.kitchen_queue.createIndex({ assignedChef: 1 });

// Insert sample data
print('🍕 Inserting sample pizzas...');

db.pizzas.insertMany([
    {
        _id: 'pizza-margherita',
        name: 'Margherita',
        description: 'Classic pizza with tomato sauce, mozzarella, and fresh basil',
        basePrice: 12.99,
        category: 'classic',
        ingredients: ['tomato sauce', 'mozzarella', 'fresh basil', 'olive oil'],
        allergens: ['gluten', 'dairy'],
        isAvailable: true,
        preparationTimeMinutes: 15,
        createdAt: new Date(),
        updatedAt: new Date()
    },
    {
        _id: 'pizza-pepperoni',
        name: 'Pepperoni',
        description: 'Traditional pepperoni pizza with tomato sauce and mozzarella',
        basePrice: 15.99,
        category: 'classic',
        ingredients: ['tomato sauce', 'mozzarella', 'pepperoni'],
        allergens: ['gluten', 'dairy'],
        isAvailable: true,
        preparationTimeMinutes: 18,
        createdAt: new Date(),
        updatedAt: new Date()
    },
    {
        _id: 'pizza-quattro-stagioni',
        name: 'Quattro Stagioni',
        description: 'Four seasons pizza with mushrooms, artichokes, ham, and olives',
        basePrice: 18.99,
        category: 'premium',
        ingredients: ['tomato sauce', 'mozzarella', 'mushrooms', 'artichokes', 'ham', 'olives'],
        allergens: ['gluten', 'dairy'],
        isAvailable: true,
        preparationTimeMinutes: 22,
        createdAt: new Date(),
        updatedAt: new Date()
    },
    {
        _id: 'pizza-vegetarian',
        name: 'Vegetarian Delight',
        description: 'Fresh vegetables on tomato sauce with mozzarella',
        basePrice: 16.99,
        category: 'vegetarian',
        ingredients: ['tomato sauce', 'mozzarella', 'bell peppers', 'mushrooms', 'red onions', 'tomatoes'],
        allergens: ['gluten', 'dairy'],
        isAvailable: true,
        preparationTimeMinutes: 20,
        createdAt: new Date(),
        updatedAt: new Date()
    },
    {
        _id: 'pizza-vegan',
        name: 'Vegan Supreme',
        description: 'Plant-based pizza with vegan cheese and fresh vegetables',
        basePrice: 19.99,
        category: 'vegan',
        ingredients: ['tomato sauce', 'vegan cheese', 'bell peppers', 'mushrooms', 'spinach', 'red onions'],
        allergens: ['gluten'],
        isAvailable: true,
        preparationTimeMinutes: 25,
        createdAt: new Date(),
        updatedAt: new Date()
    }
]);

print('👤 Inserting sample customers...');

db.customers.insertMany([
    {
        _id: 'customer-mario-rossi',
        email: 'mario.rossi@example.com',
        firstName: 'Mario',
        lastName: 'Rossi',
        phone: '+39 123 456 7890',
        address: {
            street: 'Via Roma 123',
            city: 'Naples',
            zipCode: '80100',
            country: 'Italy'
        },
        loyaltyPoints: 150,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date()
    },
    {
        _id: 'customer-luigi-verdi',
        email: 'luigi.verdi@example.com',
        firstName: 'Luigi',
        lastName: 'Verdi',
        phone: '+39 987 654 3210',
        address: {
            street: 'Corso Italia 456',
            city: 'Rome',
            zipCode: '00100',
            country: 'Italy'
        },
        loyaltyPoints: 75,
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date()
    }
]);

print('✅ Mario\'s Pizzeria database initialized successfully!');
print('📊 Collections created: customers, pizzas, orders, kitchen_queue');
print('🔍 Indexes created for optimal query performance');
print('📦 Sample data inserted: 5 pizzas, 2 customers');
