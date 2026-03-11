/**
 * companion-app/src/screens/MarketplaceScreen.js
 *
 * Browse shared models from the IntelShare AI marketplace.
 * Users can:
 *  - Browse all public models
 *  - Import a model from another user (bypasses the Learn phase entirely)
 *  - Export their own current model to share
 */

import React, { useState, useCallback } from 'react';
import {
    View, Text, StyleSheet, FlatList, TouchableOpacity,
    ActivityIndicator, RefreshControl, Modal, TextInput,
    Alert, ScrollView,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { listModels, exportModel, importModel } from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';
import { BlurView } from 'expo-blur';
import { Feather } from '@expo/vector-icons';

const COLORS = {
    bg: '#050814',
    cardBg: 'rgba(255, 255, 255, 0.03)',
    cardBorder: 'rgba(255, 255, 255, 0.1)',
    primary: '#00F0FF',
    accent: '#B026FF',
    success: '#00F0FF', 
    text: '#FFFFFF',
    textMuted: '#9CA3AF',
    textDark: '#111827',
    danger: '#FF2A93',
};

function formatDate(ts) {
    if (!ts) return '';
    return new Date(ts * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function formatSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

export default function MarketplaceScreen() {
    const [models, setModels] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refresh, setRefresh] = useState(false);
    const [error, setError] = useState(null);
    const [importingId, setImportingId] = useState(null);

    // Export modal state
    const [showExport, setShowExport] = useState(false);
    const [exportName, setExportName] = useState('');
    const [exportDesc, setExportDesc] = useState('');
    const [exportAuthor, setExportAuthor] = useState('');
    const [exporting, setExporting] = useState(false);

    const loadModels = async (isRefresh = false) => {
        if (isRefresh) setRefresh(true);
        else setLoading(true);
        setError(null);
        try {
            const res = await listModels();
            setModels(res.data.models ?? []);
        } catch {
            setError('Quantum Server Offline.\nVerify uplink connection.');
        } finally {
            setLoading(false);
            setRefresh(false);
        }
    };

    useFocusEffect(useCallback(() => { loadModels(); }, []));

    const handleImport = async (model) => {
        Alert.alert(
            `Integrate "${model.name}"?`,
            `Architect: ${model.author}. Integrating this memory block will merge its neural pathways with your local AI without overwriting existing data.`,
            [
                { text: 'Abort', style: 'cancel' },
                {
                    text: 'Integrate',
                    onPress: async () => {
                        setImportingId(model.id);
                        try {
                            await importModel(model.id);
                            Alert.alert('Integration Complete', `"${model.name}" neural weights successfully merged.`);
                        } catch (e) {
                            Alert.alert('Integration Failed', e.response?.data?.detail ?? 'An error occurred during merging.');
                        } finally {
                            setImportingId(null);
                        }
                    },
                },
            ]
        );
    };

    const handleExport = async () => {
        if (!exportName.trim()) {
            Alert.alert('Designation Required', 'Please assign a valid designation to this neural block.');
            return;
        }
        setExporting(true);
        try {
            await exportModel({
                name: exportName.trim(),
                description: exportDesc.trim(),
                author: exportAuthor.trim() || 'Anonymous Architect',
            });
            setShowExport(false);
            setExportName(''); setExportDesc(''); setExportAuthor('');
            Alert.alert('Upload Successful', 'Your neural map is now sharing globally.');
            loadModels();
        } catch (e) {
            Alert.alert('Upload Failed', e.response?.data?.detail ?? 'An error occurred during transmission.');
        } finally {
            setExporting(false);
        }
    };

    const renderModel = ({ item }) => (
        <View style={styles.cardWrapper}>
            <LinearGradient
                colors={['rgba(0, 240, 255, 0.1)', 'rgba(176, 38, 255, 0.05)']}
                start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
                style={styles.cardGradient}
            >
                <BlurView intensity={20} tint="dark" style={styles.card}>
                    <View style={styles.cardHeader}>
                        <View style={styles.modelIconBg}>
                            <Feather name="box" size={24} color={COLORS.primary} />
                        </View>
                        <View style={styles.cardTitleContainer}>
                            <Text style={styles.modelName} numberOfLines={1}>{item.name}</Text>
                            <Text style={styles.modelAuthor}>By {item.author || "Unknown Architect"}</Text>
                        </View>
                        <View style={styles.modelBadge}>
                            <Text style={styles.modelBadgeText}>{formatSize(item.file_size)}</Text>
                        </View>
                    </View>
                    
                    {item.description ? (
                        <Text style={styles.modelDesc} numberOfLines={2}>{item.description}</Text>
                    ) : (
                        <Text style={styles.modelDesc} numberOfLines={2}>No transmission data provided for this neural cluster.</Text>
                    )}

                    <View style={styles.cardFooter}>
                        <View style={styles.statContainer}>
                            <Feather name="clock" size={14} color={COLORS.textMuted} />
                            <Text style={styles.statText}>{formatDate(item.created_at)}</Text>
                        </View>
                        <TouchableOpacity
                            style={[
                                styles.downloadBtn, 
                                importingId === item.id && { opacity: 0.6 }
                            ]}
                            onPress={() => handleImport(item)}
                            disabled={importingId === item.id}
                        >
                            {importingId === item.id ? (
                                <ActivityIndicator size="small" color={COLORS.primary} />
                            ) : (
                                <>
                                    <Feather name="arrow-down-circle" size={18} color={COLORS.primary} style={{ marginRight: 6 }} />
                                    <Text style={styles.downloadBtnText}>Integrate</Text>
                                </>
                            )}
                        </TouchableOpacity>
                    </View>
                </BlurView>
            </LinearGradient>
        </View>
    );

    return (
        <View style={styles.container}>
            {/* Background glowing orbs */}
            <View style={styles.glowTopLeft} />
            <View style={styles.glowBottomRight} />

            <View style={styles.header}>
                <Text style={styles.title}>Neural Marketplace</Text>
                <Text style={styles.subtitle}>Discover and deploy advanced AI parameters</Text>
                
                <TouchableOpacity style={styles.actionBtn} onPress={() => setShowExport(true)}>
                    <LinearGradient 
                        colors={['rgba(255, 255, 255, 0.05)', 'rgba(255, 255, 255, 0.02)']} 
                        style={styles.actionBtnGradient}
                    >
                        <Feather name="upload-cloud" size={20} color={COLORS.text} style={styles.actionBtnIcon} />
                        <Text style={styles.actionBtnText}>Share Network Map</Text>
                    </LinearGradient>
                </TouchableOpacity>
            </View>

            {loading ? (
                <View style={styles.center}>
                    <ActivityIndicator size="large" color={COLORS.primary} />
                    <Text style={[styles.muted, { marginTop: 12 }]}>Syncing with Quantum Server…</Text>
                </View>
            ) : error ? (
                <View style={styles.center}>
                    <Feather name="server" size={48} color={COLORS.textMuted} style={{ marginBottom: 16, opacity: 0.5 }} />
                    <Text style={styles.errorText}>{error}</Text>
                    <TouchableOpacity onPress={() => loadModels()} style={styles.retryBtn}>
                        <LinearGradient colors={[COLORS.primary, '#00A3FF']} style={styles.btnGradient}>
                            <Text style={styles.retryText}>Retry Uplink</Text>
                        </LinearGradient>
                    </TouchableOpacity>
                </View>
            ) : models.length === 0 ? (
                <View style={styles.center}>
                    <Feather name="inbox" size={48} color={COLORS.textMuted} style={{ marginBottom: 16, opacity: 0.5 }} />
                    <Text style={styles.emptyText}>No network architectures found in the database.</Text>
                </View>
            ) : (
                <FlatList
                    data={models}
                    keyExtractor={item => item.id}
                    renderItem={renderModel}
                    contentContainerStyle={styles.list}
                    refreshControl={
                        <RefreshControl
                            refreshing={refresh}
                            onRefresh={() => loadModels(true)}
                            tintColor={COLORS.primary}
                        />
                    }
                    ListHeaderComponent={
                        <Text style={styles.countText}>{models.length} neural map{models.length !== 1 ? 's' : ''} available</Text>
                    }
                />
            )}

            {/* ── Export modal ── */}
            <Modal visible={showExport} animationType="slide" transparent>
                <BlurView intensity={80} tint="dark" style={styles.modalOverlay}>
                    <View style={styles.modalCard}>
                        <View style={styles.modalHeader}>
                            <View>
                                <Text style={styles.modalTitle}>Upload Neural Map</Text>
                                <Text style={styles.modalSubtitle}>
                                    Share your trained parameters globally.
                                </Text>
                            </View>
                            <TouchableOpacity onPress={() => setShowExport(false)} style={styles.closeBtn}>
                                <Feather name="x" size={24} color={COLORS.textMuted} />
                            </TouchableOpacity>
                        </View>
                        
                        <ScrollView showsVerticalScrollIndicator={false}>
                            <View style={styles.inputContainer}>
                                <Text style={styles.inputLabel}>Designation</Text>
                                <View style={styles.inputWrapper}>
                                    <Feather name="tag" size={18} color={COLORS.textMuted} style={styles.inputIcon} />
                                    <TextInput
                                        style={styles.modalInput}
                                        value={exportName}
                                        onChangeText={setExportName}
                                        placeholder="e.g. Optimized Vision Core v2"
                                        placeholderTextColor={COLORS.textMuted}
                                    />
                                </View>
                            </View>

                            <View style={styles.inputContainer}>
                                <Text style={styles.inputLabel}>Transmission Data</Text>
                                <View style={[styles.inputWrapper, { height: 100, alignItems: 'flex-start', paddingTop: 12 }]}>
                                    <Feather name="align-left" size={18} color={COLORS.textMuted} style={[styles.inputIcon, { marginTop: 2 }]} />
                                    <TextInput
                                        style={[styles.modalInput, styles.textArea]}
                                        value={exportDesc}
                                        onChangeText={setExportDesc}
                                        placeholder="Describe the capabilities of this network..."
                                        placeholderTextColor={COLORS.textMuted}
                                        multiline
                                        textAlignVertical="top"
                                    />
                                </View>
                            </View>

                            <View style={styles.inputContainer}>
                                <Text style={styles.inputLabel}>Architect ID</Text>
                                <View style={styles.inputWrapper}>
                                    <Feather name="user" size={18} color={COLORS.textMuted} style={styles.inputIcon} />
                                    <TextInput
                                        style={styles.modalInput}
                                        value={exportAuthor}
                                        onChangeText={setExportAuthor}
                                        placeholder="Your alias (optional)"
                                        placeholderTextColor={COLORS.textMuted}
                                    />
                                </View>
                            </View>

                            <TouchableOpacity 
                                style={styles.submitBtn} 
                                onPress={handleExport}
                                disabled={exporting}
                            >
                                <LinearGradient 
                                    colors={[COLORS.primary, '#00A3FF']} 
                                    style={[styles.submitBtnGradient, exporting && { opacity: 0.7 }]}
                                    start={{x: 0, y: 0}} end={{x: 1, y: 1}}
                                >
                                    {exporting ? (
                                        <ActivityIndicator color={COLORS.textDark} />
                                    ) : (
                                        <>
                                            <Feather name="upload" size={18} color={COLORS.textDark} style={styles.submitBtnIcon} />
                                            <Text style={styles.submitBtnText}>Initialize Upload</Text>
                                        </>
                                    )}
                                </LinearGradient>
                            </TouchableOpacity>
                        </ScrollView>
                    </View>
                </BlurView>
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: COLORS.bg },
    glowTopLeft: { position: 'absolute', top: -50, left: -100, width: 400, height: 400, borderRadius: 200, backgroundColor: 'rgba(0, 240, 255, 0.08)', opacity: 0.8, blurRadius: 80 },
    glowBottomRight: { position: 'absolute', bottom: -50, right: -100, width: 300, height: 300, borderRadius: 150, backgroundColor: 'rgba(176, 38, 255, 0.08)', opacity: 0.8, blurRadius: 70 },
    
    header: { paddingTop: 60, paddingHorizontal: 24, paddingBottom: 10, zIndex: 10 },
    title: { fontFamily: 'Outfit_800ExtraBold', fontSize: 32, color: COLORS.text, marginBottom: 8, letterSpacing: 0.5 },
    subtitle: { fontFamily: 'Outfit_400Regular', fontSize: 15, color: COLORS.textMuted, lineHeight: 22, marginBottom: 20 },
    
    actionBtn: { borderRadius: 12, overflow: 'hidden', borderWidth: 1, borderColor: COLORS.cardBorder, marginBottom: 10 },
    actionBtnGradient: { paddingVertical: 14, flexDirection: 'row', justifyContent: 'center', alignItems: 'center' },
    actionBtnIcon: { marginRight: 8 },
    actionBtnText: { fontFamily: 'Outfit_600SemiBold', fontSize: 14, color: COLORS.text, letterSpacing: 0.5 },
    
    center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 24, paddingBottom: 100 },
    errorText: { fontFamily: 'Outfit_600SemiBold', color: '#EF4444', textAlign: 'center', marginBottom: 20, fontSize: 15, lineHeight: 22 },
    emptyText: { fontFamily: 'Outfit_400Regular', color: COLORS.textMuted, textAlign: 'center', fontSize: 15, lineHeight: 22 },
    muted: { fontFamily: 'Outfit_400Regular', color: COLORS.textMuted, textAlign: 'center', fontSize: 15, lineHeight: 22 },
    retryBtn: { overflow: 'hidden', borderRadius: 12 },
    btnGradient: { paddingHorizontal: 24, paddingVertical: 12 },
    retryText: { color: COLORS.textDark, fontFamily: 'Outfit_800ExtraBold', fontSize: 14, letterSpacing: 0.5 },
    
    list: { paddingHorizontal: 16, paddingBottom: 120, paddingTop: 10 },
    countText: { fontFamily: 'Outfit_600SemiBold', fontSize: 11, color: COLORS.textMuted, marginVertical: 12, textTransform: 'uppercase', letterSpacing: 1.2 },
    cardWrapper: { marginBottom: 16, borderRadius: 20, overflow: 'hidden' },
    cardGradient: { padding: 1 },
    card: { backgroundColor: COLORS.cardBg, borderRadius: 20, padding: 20 },
    cardHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
    modelIconBg: { width: 48, height: 48, borderRadius: 14, backgroundColor: 'rgba(0, 240, 255, 0.1)', justifyContent: 'center', alignItems: 'center', marginRight: 16, borderWidth: 1, borderColor: 'rgba(0, 240, 255, 0.2)' },
    cardTitleContainer: { flex: 1 },
    modelName: { fontFamily: 'Outfit_800ExtraBold', fontSize: 18, color: COLORS.text, marginBottom: 4 },
    modelAuthor: { fontFamily: 'Outfit_400Regular', fontSize: 13, color: COLORS.textMuted },
    modelBadge: { backgroundColor: 'rgba(255, 255, 255, 0.1)', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 6 },
    modelBadgeText: { fontFamily: 'Outfit_600SemiBold', fontSize: 11, color: COLORS.text },
    modelDesc: { fontFamily: 'Outfit_400Regular', fontSize: 14, color: COLORS.textMuted, lineHeight: 22, marginBottom: 20 },
    cardFooter: { flexDirection: 'row', alignItems: 'center', paddingTop: 16, borderTopWidth: 1, borderTopColor: COLORS.cardBorder },
    statContainer: { flexDirection: 'row', alignItems: 'center', marginRight: 16, backgroundColor: 'rgba(255, 255, 255, 0.05)', paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8 },
    statText: { fontFamily: 'Outfit_600SemiBold', fontSize: 12, color: COLORS.text, marginLeft: 6 },
    downloadBtn: { marginLeft: 'auto', flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(0, 240, 255, 0.1)', paddingHorizontal: 16, paddingVertical: 8, borderRadius: 8, borderWidth: 1, borderColor: 'rgba(0, 240, 255, 0.2)' },
    downloadBtnText: { fontFamily: 'Outfit_800ExtraBold', fontSize: 13, color: COLORS.primary, letterSpacing: 0.5 },

    modalOverlay: { flex: 1, justifyContent: 'flex-end' },
    modalCard: { backgroundColor: '#0B1120', borderTopLeftRadius: 32, borderTopRightRadius: 32, padding: 24, paddingBottom: 40, borderWidth: 1, borderColor: COLORS.cardBorder, borderBottomWidth: 0, maxHeight: '80%' },
    modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 },
    modalTitle: { fontFamily: 'Outfit_800ExtraBold', fontSize: 24, color: COLORS.text, marginBottom: 6 },
    modalSubtitle: { fontFamily: 'Outfit_400Regular', fontSize: 14, color: COLORS.textMuted, lineHeight: 20, maxWidth: '80%' },
    closeBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: COLORS.cardBg, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: COLORS.cardBorder },
    
    inputContainer: { marginBottom: 20 },
    inputLabel: { fontFamily: 'Outfit_600SemiBold', fontSize: 14, color: COLORS.text, marginBottom: 10, letterSpacing: 0.5 },
    inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.bg, borderRadius: 16, borderWidth: 1, borderColor: COLORS.cardBorder, paddingHorizontal: 16, height: 56 },
    inputIcon: { marginRight: 12 },
    modalInput: { flex: 1, fontFamily: 'Outfit_400Regular', fontSize: 15, color: COLORS.text },
    textArea: { height: '100%' },
    
    submitBtn: { borderRadius: 16, overflow: 'hidden', marginTop: 10, shadowColor: COLORS.primary, shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.3, shadowRadius: 16, marginBottom: 20 },
    submitBtnGradient: { flexDirection: 'row', paddingVertical: 18, justifyContent: 'center', alignItems: 'center' },
    submitBtnIcon: { marginRight: 8 },
    submitBtnText: { fontFamily: 'Outfit_800ExtraBold', fontSize: 16, color: COLORS.textDark, letterSpacing: 0.5 },
});
