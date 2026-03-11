/**
 * companion-app/src/screens/SettingsScreen.js
 *
 * Lets the user configure the Raspberry Pi IP address and verify the connection.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
    View, Text, StyleSheet, TextInput, TouchableOpacity,
    ActivityIndicator, ScrollView, Alert, Animated, Easing
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { checkHealth } from '../services/api';
import api from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';
import { Feather } from '@expo/vector-icons';

const COLORS = {
    bg: '#050814',
    cardBg: 'rgba(255, 255, 255, 0.03)',
    cardBorder: 'rgba(255, 255, 255, 0.1)',
    primary: '#00F0FF',
    primaryDim: 'rgba(0, 240, 255, 0.2)',
    accent: '#B026FF',
    success: '#00F0FF', 
    danger: '#FF2A93',
    text: '#FFFFFF',
    textMuted: '#9CA3AF',
    textDark: '#111827',
};

const IP_KEY = 'pi_ip';

export default function SettingsScreen() {
    const [ip, setIp] = useState('192.168.1.100');
    const [status, setStatus] = useState(null);   // null | 'ok' | 'fail'
    const [testing, setTesting] = useState(false);
    
    // Animation for telemetry ping
    const pulseAnim = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        AsyncStorage.getItem(IP_KEY).then(saved => {
            if (saved) { setIp(saved); api.defaults.baseURL = `http://${saved}:8000`; }
        });
    }, []);

    useEffect(() => {
        if (status === 'ok') {
            Animated.loop(
                Animated.sequence([
                    Animated.timing(pulseAnim, {
                        toValue: 1,
                        duration: 1500,
                        easing: Easing.out(Easing.ease),
                        useNativeDriver: true,
                    }),
                    Animated.timing(pulseAnim, {
                        toValue: 0,
                        duration: 1500,
                        easing: Easing.in(Easing.ease),
                        useNativeDriver: true,
                    })
                ])
            ).start();
        } else {
            pulseAnim.setValue(0);
        }
    }, [status]);

    const saveIp = async () => {
        const trimmed = ip.trim();
        await AsyncStorage.setItem(IP_KEY, trimmed);
        api.defaults.baseURL = `http://${trimmed}:8000`;
        Alert.alert('Configuration Saved', `Uplink IP set to ${trimmed}`);
    };

    const testConnection = async () => {
        setTesting(true);
        setStatus(null);
        try {
            await checkHealth();
            setStatus('ok');
        } catch {
            setStatus('fail');
        } finally {
            setTesting(false);
        }
    };

    return (
        <ScrollView style={styles.container} contentContainerStyle={styles.content}>
            {/* Background elements */}
            <View style={styles.glowTopRight} />

            <View style={styles.header}>
                <Text style={styles.headerTitle}>System Configuration</Text>
                <Text style={styles.headerSubtitle}>Manage uplink parameters and local architecture</Text>
            </View>

            <Text style={styles.sectionTitle}>QUANTUM UPLINK (RASPBERRY PI)</Text>

            <View style={styles.cardWrapper}>
                <LinearGradient
                    colors={['rgba(255, 255, 255, 0.05)', 'rgba(255, 255, 255, 0.01)']}
                    start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                    style={styles.cardGradient}
                >
                    <View style={styles.card}>
                        <View style={styles.inputContainer}>
                            <View style={styles.inputWrapper}>
                                <Feather name="wifi" size={18} color={COLORS.primary} style={styles.inputIcon} />
                                <TextInput
                                    style={styles.input}
                                    value={ip}
                                    onChangeText={setIp}
                                    placeholder="e.g. 192.168.1.100"
                                    placeholderTextColor={COLORS.textMuted}
                                    keyboardType="numeric"
                                    autoCorrect={false}
                                />
                            </View>
                            <Text style={styles.hint}>
                                Ensure mobile device and computation unit are on the same local subnet.
                            </Text>
                        </View>
                        
                        <View style={styles.actionRow}>
                            <TouchableOpacity style={styles.saveBtn} onPress={saveIp}>
                                <Text style={styles.saveBtnText}>Save Parameters</Text>
                            </TouchableOpacity>
                        </View>

                        <View style={styles.telemetrySection}>
                            <TouchableOpacity
                                style={[styles.testBtn, testing && { opacity: 0.6 }]}
                                onPress={testConnection}
                                disabled={testing}
                            >
                                <LinearGradient
                                    colors={['rgba(0, 240, 255, 0.15)', 'rgba(0, 240, 255, 0.05)']}
                                    start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                                    style={styles.testBtnGradient}
                                >
                                    {testing
                                        ? <ActivityIndicator size="small" color={COLORS.primary} />
                                        : <>
                                            <Feather name="activity" size={16} color={COLORS.primary} style={{ marginRight: 8 }} />
                                            <Text style={styles.testBtnText}>Initiate Telemetry Ping</Text>
                                          </>}
                                </LinearGradient>
                            </TouchableOpacity>

                            {status === 'ok' && (
                                <View style={styles.statusBoxOk}>
                                    <Animated.View style={[styles.pulseIndicator, { opacity: pulseAnim }]} />
                                    <Feather name="check-circle" size={18} color={COLORS.success} />
                                    <Text style={styles.statusTextOk}>Uplink Verified. System Online.</Text>
                                </View>
                            )}
                            
                            {status === 'fail' && (
                                <View style={styles.statusBoxFail}>
                                    <Feather name="alert-triangle" size={18} color={COLORS.danger} />
                                    <Text style={styles.statusTextFail}>Uplink Offline. Verify IP & port 8000.</Text>
                                </View>
                            )}
                        </View>
                    </View>
                </LinearGradient>
            </View>

            <Text style={styles.sectionTitle}>DIAGNOSTICS & INFO</Text>
            
            <View style={styles.cardWrapper}>
                <LinearGradient
                    colors={['rgba(255, 255, 255, 0.05)', 'rgba(255, 255, 255, 0.01)']}
                    start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                    style={styles.cardGradient}
                >
                    <View style={styles.card}>
                        {[
                            ['System Module', 'IntelShare Vision Core', 'cpu'],
                            ['Current Build Version', 'v1.0.4.Beta', 'git-commit'],
                            ['Data Transmission Port', '8000', 'radio'],
                            ['Hardware Accelerator', 'Active', 'zap']
                        ].map(([k, v, icon], index, arr) => (
                            <View key={k} style={[styles.infoRow, index === arr.length - 1 && { borderBottomWidth: 0 }]}>
                                <View style={styles.infoKeyContainer}>
                                    <Feather name={icon} size={14} color={COLORS.textMuted} style={styles.infoIcon} />
                                    <Text style={styles.infoKey}>{k}</Text>
                                </View>
                                <Text style={styles.infoVal}>{v}</Text>
                            </View>
                        ))}
                    </View>
                </LinearGradient>
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    glowTopRight: { position: 'absolute', top: -50, right: -100, width: 300, height: 300, borderRadius: 150, backgroundColor: 'rgba(0, 240, 255, 0.08)', opacity: 0.8, blurRadius: 70 },
    
    content: { padding: 24, paddingBottom: 40, paddingTop: 60 },
    
    header: { marginBottom: 30 },
    headerTitle: { fontFamily: 'Outfit_800ExtraBold', fontSize: 32, color: COLORS.text, marginBottom: 8, letterSpacing: 0.5 },
    headerSubtitle: { fontFamily: 'Outfit_400Regular', fontSize: 15, color: COLORS.textMuted, lineHeight: 22 },

    sectionTitle: { fontFamily: 'Outfit_600SemiBold', fontSize: 11, color: COLORS.textMuted, textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 12, marginLeft: 4, marginTop: 10 },
    
    cardWrapper: { borderRadius: 20, overflow: 'hidden', marginBottom: 24 },
    cardGradient: { padding: 1 },
    card: { backgroundColor: COLORS.cardBg, borderRadius: 20, padding: 20 },
    
    inputContainer: { marginBottom: 16 },
    inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.bg, borderRadius: 14, borderWidth: 1, borderColor: COLORS.cardBorder, paddingHorizontal: 16, height: 56, marginBottom: 8 },
    inputIcon: { marginRight: 12, opacity: 0.8 },
    input: { flex: 1, fontFamily: 'Outfit_400Regular', color: COLORS.primary, fontSize: 18, letterSpacing: 1 },
    hint: { fontFamily: 'Outfit_400Regular', fontSize: 13, color: COLORS.textMuted, lineHeight: 18, marginLeft: 4 },
    
    actionRow: { marginBottom: 24 },
    saveBtn: { backgroundColor: 'rgba(255, 255, 255, 0.05)', borderRadius: 12, paddingVertical: 14, alignItems: 'center', borderWidth: 1, borderColor: COLORS.cardBorder },
    saveBtnText: { fontFamily: 'Outfit_600SemiBold', color: COLORS.text, fontSize: 14, letterSpacing: 0.5 },
    
    telemetrySection: { backgroundColor: COLORS.bg, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: 'rgba(0, 240, 255, 0.15)' },
    testBtn: { borderRadius: 12, overflow: 'hidden', marginBottom: 12 },
    testBtnGradient: { paddingVertical: 14, flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
    testBtnText: { fontFamily: 'Outfit_800ExtraBold', color: COLORS.primary, fontSize: 14, letterSpacing: 0.5 },
    
    statusBoxOk: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0, 240, 255, 0.08)', padding: 12, borderRadius: 10, borderWidth: 1, borderColor: 'rgba(0, 240, 255, 0.2)' },
    pulseIndicator: { position: 'absolute', left: 12, top: 12, width: 18, height: 18, borderRadius: 9, backgroundColor: COLORS.success, zIndex: -1 },
    statusTextOk: { fontFamily: 'Outfit_600SemiBold', color: COLORS.success, fontSize: 13, marginLeft: 10, letterSpacing: 0.3 },
    
    statusBoxFail: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255, 42, 147, 0.08)', padding: 12, borderRadius: 10, borderWidth: 1, borderColor: 'rgba(255, 42, 147, 0.2)' },
    statusTextFail: { fontFamily: 'Outfit_600SemiBold', color: COLORS.danger, fontSize: 13, marginLeft: 10, letterSpacing: 0.3 },
    
    infoRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 14, borderBottomWidth: 1, borderColor: COLORS.cardBorder },
    infoKeyContainer: { flexDirection: 'row', alignItems: 'center' },
    infoIcon: { marginRight: 8, opacity: 0.7 },
    infoKey: { fontFamily: 'Outfit_400Regular', color: COLORS.textMuted, fontSize: 13 },
    infoVal: { fontFamily: 'Outfit_600SemiBold', color: COLORS.text, fontSize: 13, letterSpacing: 0.3 },
});
