/**
 * companion-app/src/screens/SettingsScreen.js
 *
 * Lets the user configure the Raspberry Pi IP address and verify the connection.
 */

import React, { useState, useEffect } from 'react';
import {
    View, Text, StyleSheet, TextInput, TouchableOpacity,
    ActivityIndicator, Switch, ScrollView, Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { checkHealth } from '../services/api';
import api from '../services/api';

const COLORS = {
    bg: '#0A0F1E',
    card: '#111827',
    border: '#1F2937',
    primary: '#3B82F6',
    success: '#10B981',
    danger: '#EF4444',
    text: '#F9FAFB',
    muted: '#6B7280',
};

const IP_KEY = 'pi_ip';

export default function SettingsScreen() {
    const [ip, setIp] = useState('192.168.1.100');
    const [status, setStatus] = useState(null);   // null | 'ok' | 'fail'
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        AsyncStorage.getItem(IP_KEY).then(saved => {
            if (saved) { setIp(saved); api.defaults.baseURL = `http://${saved}:8000`; }
        });
    }, []);

    const saveIp = async () => {
        const trimmed = ip.trim();
        await AsyncStorage.setItem(IP_KEY, trimmed);
        api.defaults.baseURL = `http://${trimmed}:8000`;
        Alert.alert('Saved', `Pi IP set to ${trimmed}`);
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
            <Text style={styles.sectionTitle}>Raspberry Pi Connection</Text>

            <View style={styles.card}>
                <Text style={styles.label}>Pi IP Address</Text>
                <TextInput
                    style={styles.input}
                    value={ip}
                    onChangeText={setIp}
                    placeholder="e.g. 192.168.1.100"
                    placeholderTextColor={COLORS.muted}
                    keyboardType="numeric"
                    autoCorrect={false}
                />
                <Text style={styles.hint}>
                    Ensure your phone and the Raspberry Pi are on the same Wi-Fi network.
                </Text>
                <View style={styles.btnRow}>
                    <TouchableOpacity style={styles.saveBtn} onPress={saveIp}>
                        <Text style={styles.saveBtnText}>Save</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.testBtn, testing && { opacity: 0.6 }]}
                        onPress={testConnection}
                        disabled={testing}
                    >
                        {testing
                            ? <ActivityIndicator size="small" color={COLORS.primary} />
                            : <Text style={styles.testBtnText}>Test Connection</Text>}
                    </TouchableOpacity>
                </View>

                {status === 'ok' && (
                    <View style={styles.statusRow}>
                        <Text style={styles.statusOk}>✓ Connected to IntelShare AI</Text>
                    </View>
                )}
                {status === 'fail' && (
                    <View style={styles.statusRow}>
                        <Text style={styles.statusFail}>✗ Cannot reach Pi — check IP and port 8000</Text>
                    </View>
                )}
            </View>

            <Text style={styles.sectionTitle}>About</Text>
            <View style={styles.card}>
                {[
                    ['App', 'IntelShare AI Companion'],
                    ['Version', '1.0.0'],
                    ['Backend Port', '8000'],
                ].map(([k, v]) => (
                    <View key={k} style={styles.infoRow}>
                        <Text style={styles.infoKey}>{k}</Text>
                        <Text style={styles.infoVal}>{v}</Text>
                    </View>
                ))}
            </View>
        </ScrollView>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    content: { padding: 16, paddingBottom: 40 },
    sectionTitle: { fontSize: 11, color: COLORS.muted, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1, marginTop: 20, marginBottom: 10, marginLeft: 4 },
    card: { backgroundColor: COLORS.card, borderRadius: 16, borderWidth: 1, borderColor: COLORS.border, padding: 16, marginBottom: 8 },
    label: { fontSize: 13, color: COLORS.muted, fontWeight: '600', marginBottom: 8 },
    input: { backgroundColor: '#1F2937', borderRadius: 10, padding: 12, color: COLORS.text, fontSize: 16, fontFamily: 'monospace', marginBottom: 8 },
    hint: { fontSize: 12, color: COLORS.muted, lineHeight: 18, marginBottom: 14 },
    btnRow: { flexDirection: 'row', gap: 8 },
    saveBtn: { flex: 1, backgroundColor: COLORS.primary, borderRadius: 10, padding: 12, alignItems: 'center' },
    saveBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
    testBtn: { flex: 1, borderWidth: 1, borderColor: COLORS.primary, borderRadius: 10, padding: 12, alignItems: 'center' },
    testBtnText: { color: COLORS.primary, fontWeight: '700', fontSize: 14 },
    statusRow: { marginTop: 12 },
    statusOk: { color: COLORS.success, fontWeight: '700', fontSize: 13 },
    statusFail: { color: COLORS.danger, fontWeight: '700', fontSize: 13 },
    infoRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderColor: COLORS.border },
    infoKey: { color: COLORS.muted, fontSize: 13 },
    infoVal: { color: COLORS.text, fontSize: 13, fontWeight: '600' },
});
