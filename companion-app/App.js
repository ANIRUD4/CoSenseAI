/**
 * companion-app/App.js
 *
 * IntelShare AI Companion App
 * React Native (Expo) mobile application for managing action mappings
 * and the model marketplace.
 */

import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text, View } from 'react-native';

import ActionMappingScreen from './src/screens/ActionMappingScreen';
import MarketplaceScreen from './src/screens/MarketplaceScreen';
import SettingsScreen from './src/screens/SettingsScreen';

const Tab = createBottomTabNavigator();

const icon = (emoji, focused) => (
  <View style={{ alignItems: 'center', justifyContent: 'center' }}>
    <Text style={{ fontSize: 22, opacity: focused ? 1 : 0.45 }}>{emoji}</Text>
  </View>
);

export default function App() {
  return (
    <NavigationContainer>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: '#111827', borderBottomColor: '#1F2937', borderBottomWidth: 1 },
          headerTintColor: '#F9FAFB',
          headerTitleStyle: { fontWeight: '800', letterSpacing: 0.3 },
          tabBarStyle: { backgroundColor: '#111827', borderTopColor: '#1F2937', borderTopWidth: 1, height: 70, paddingBottom: 10 },
          tabBarActiveTintColor: '#3B82F6',
          tabBarInactiveTintColor: '#6B7280',
          tabBarLabelStyle: { fontSize: 11, fontWeight: '700', marginTop: 2 },
        }}
      >
        <Tab.Screen
          name="Actions"
          component={ActionMappingScreen}
          options={{
            title: 'Action Mapping',
            tabBarLabel: 'Actions',
            tabBarIcon: ({ focused }) => icon('⚡', focused),
            headerRight: () => (
              <Text style={{ color: '#6B7280', fontSize: 12, marginRight: 16 }}>
                Pull to refresh
              </Text>
            ),
          }}
        />
        <Tab.Screen
          name="Marketplace"
          component={MarketplaceScreen}
          options={{
            title: 'Marketplace',
            tabBarLabel: 'Marketplace',
            tabBarIcon: ({ focused }) => icon('🛒', focused),
          }}
        />
        <Tab.Screen
          name="Settings"
          component={SettingsScreen}
          options={{
            title: 'Settings',
            tabBarLabel: 'Settings',
            tabBarIcon: ({ focused }) => icon('⚙️', focused),
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}
