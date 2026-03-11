/**
 * companion-app/App.js
 *
 * IntelShare AI Companion App
 * React Native (Expo) mobile application for managing action mappings
 * and the model marketplace.
 */

import React, { useState, useEffect } from 'react';
import { StatusBar } from 'expo-status-bar';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text, View, StyleSheet } from 'react-native';
import * as Font from 'expo-font';
import { Outfit_400Regular, Outfit_600SemiBold, Outfit_800ExtraBold } from '@expo-google-fonts/outfit';
import { BlurView } from 'expo-blur';
import { Feather } from '@expo/vector-icons';

import ActionMappingScreen from './src/screens/ActionMappingScreen';
import MarketplaceScreen from './src/screens/MarketplaceScreen';
import SettingsScreen from './src/screens/SettingsScreen';
import LabelDetailsScreen from './src/screens/LabelDetailsScreen';
import { createStackNavigator } from '@react-navigation/stack';

const Tab = createBottomTabNavigator();
const ActionStack = createStackNavigator();

function ActionStackScreen() {
  return (
    <ActionStack.Navigator screenOptions={{ 
      headerStyle: { backgroundColor: 'transparent', elevation: 0, shadowOpacity: 0 },
      headerTransparent: true,
      headerTintColor: '#F9FAFB',
      headerTitleStyle: { fontFamily: 'Outfit_800ExtraBold', fontSize: 22, letterSpacing: 0.5 },
      headerBackTitleVisible: false,
    }}>
      <ActionStack.Screen 
        name="ActionMappingList" 
        component={ActionMappingScreen} 
        options={{ title: 'Memory' }}
      />
      <ActionStack.Screen 
        name="LabelDetails" 
        component={LabelDetailsScreen} 
        options={{ title: '' }}
      />
    </ActionStack.Navigator>
  );
}

const iconBadge = (name, focused) => (
  <View style={[styles.iconContainer, focused && styles.iconContainerFocused]}>
    <Feather name={name} size={22} color={focused ? '#00F0FF' : '#4B5563'} />
  </View>
);

export default function App() {
  const [fontsLoaded, setFontsLoaded] = useState(false);

  useEffect(() => {
    async function loadFonts() {
      await Font.loadAsync({
        Outfit_400Regular,
        Outfit_600SemiBold,
        Outfit_800ExtraBold,
      });
      setFontsLoaded(true);
    }
    loadFonts();
  }, []);

  if (!fontsLoaded) {
    return null; // Await fonts
  }

  return (
    <NavigationContainer theme={{ colors: { background: '#050814' } }}>
      <StatusBar style="light" />
      <Tab.Navigator
        screenOptions={{
          headerStyle: { backgroundColor: 'transparent', elevation: 0, shadowOpacity: 0 },
          headerTransparent: true,
          headerTintColor: '#F9FAFB',
          headerTitleStyle: { fontFamily: 'Outfit_800ExtraBold', fontSize: 26, letterSpacing: 0.5 },
          tabBarStyle: { position: 'absolute', borderTopWidth: 0, elevation: 0, height: 85 },
          tabBarBackground: () => (
            <BlurView tint="dark" intensity={80} style={StyleSheet.absoluteFill} />
          ),
          tabBarActiveTintColor: '#00F0FF',
          tabBarInactiveTintColor: '#4B5563',
          tabBarLabelStyle: { fontFamily: 'Outfit_600SemiBold', fontSize: 11, marginBottom: 10 },
        }}
      >
        <Tab.Screen
          name="ActionsStack"
          component={ActionStackScreen}
          options={{
            headerShown: false,
            tabBarLabel: 'Memory',
            tabBarIcon: ({ focused }) => iconBadge('cpu', focused),
          }}
        />
        <Tab.Screen
          name="Marketplace"
          component={MarketplaceScreen}
          options={{
            title: 'Nexus',
            tabBarLabel: 'Nexus',
            tabBarIcon: ({ focused }) => iconBadge('globe', focused),
          }}
        />
        <Tab.Screen
          name="Settings"
          component={SettingsScreen}
          options={{
            title: 'System',
            tabBarLabel: 'System',
            tabBarIcon: ({ focused }) => iconBadge('sliders', focused),
          }}
        />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

const styles = StyleSheet.create({
  iconContainer: {
    alignItems: 'center', 
    justifyContent: 'center',
    width: 48,
    height: 32,
    borderRadius: 16,
    marginTop: 8
  },
  iconContainerFocused: {
    backgroundColor: 'rgba(0, 240, 255, 0.1)',
  }
});
