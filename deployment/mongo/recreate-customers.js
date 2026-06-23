// Recreate customers collection with proper schema
db = db.getSiblingDB('mario_pizzeria');

// Drop existing collection if it exists
try {
    db.customers.drop();
    print('Dropped existing customers collection');
} catch (e) {
    print('No existing collection to drop');
}

// Create collection with validation schema
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

// Create indexes
db.customers.createIndex({ "id": 1 }, { unique: true });
db.customers.createIndex({ "state.email": 1 }, { unique: true });
db.customers.createIndex({ "state.user_id": 1 });
db.customers.createIndex({ "state.phone": 1 });

print('✅ Customers collection recreated with proper schema for AggregateRoot');
